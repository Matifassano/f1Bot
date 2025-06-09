from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from llm.llm import F1AnalysisLLM
from data.driver_analysis import get_full_analysis
from db.dbHandler import get_db_connection

load_dotenv()

class F1TelegramBot:
    def __init__(self):
        """
        Initializes the F1 Telegram bot.
        Configures the LLM model and gets the Telegram token from environment variables.
        
        Functions:
        - Creates an instance of the LLM model for text analysis
        - Loads the Telegram authentication token from environment variables
        """
        self.llm = F1AnalysisLLM()
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handles the /start command of the bot.
        Sends a welcome message with example questions it can answer.
        
        Functions:
        - Responds to the /start command
        - Response is in Spanish
        - Shows examples of how to interact with the bot
        - Uses emojis to make the interface more friendly
        """
        await update.message.reply_text(
            "¡Hola! Soy tu bot de análisis de franco en la F1 🏎️\n"
            "Pregúntame sobre su rendimiento en algún circuito:\n"
            "- 'Cómo le fue a Colapinto en Imola 2025'\n"
            "- 'Analiza el rendimiento de Colapinto en Monaco 2024'\n"
            "- 'Cómo le fue a Colapinto en Monaco 2024'"
        )
        last_query_time = context.user_data.get('last_query_time')
        if last_query_time and datetime.now() - last_query_time < timedelta(seconds=30):
            await update.message.reply_text("Espera 30 segundos entre consultas, no seas tan rapido como Franco! 🤣")
            return
        context.user_data['last_query_time'] = datetime.now()

    async def handle_f1_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Processes user queries about F1.
        
        Steps:
        1. Extracts parameters (driver, year, circuit) using LLM
        2. Maps driver name to code and number
        3. Generates analysis graphs
        4. Gets graphs from database
        5. Generates analysis summary using LLM
        6. Sends summary and graphs to user
        
        Functions:
        - Processes user message
        - Shows status messages during process
        - Handles errors at each step
        - Sends results in text and image format
        """
        user_message = update.message.text
        chat_id = update.effective_chat.id
        
        processing_msg = await update.message.reply_text("🔄 Espera un momento que lo analizo...")
        
        try:
            params = self.llm.extract_analysis_params(user_message)
            
            if not params:
                await processing_msg.edit_text("❌ No pude entender tu pregunta. Intenta ser más específico.")
                return
            
            driver_mapping = {
                'colapinto': {'name': 'COL', 'number': '43'},
                'COL': {'name': 'COL', 'number': '43'}, 
                'franco': {'name': 'COL', 'number': '43'}, 
            }
            
            pilot_key = params['pilot'].lower()
            if pilot_key not in driver_mapping:
                await processing_msg.edit_text(f"❌ No encontre el piloto '{params['pilot']}', proba escribirlo con mayuscula.")
                return
            
            driver_info = driver_mapping[pilot_key]
            
            await processing_msg.edit_text("📊 Generando gráficos...")
            
            try:
                get_full_analysis(
                    params['year'], 
                    params['track'], 
                    driver_info['name'], 
                    driver_info['number']
                )
                
                graphs = self.get_event_graphs(params['year'], params['track'], driver_info['name'])
                
                summary = self.llm.generate_analysis_summary(params, graphs)
                
                await processing_msg.edit_text("📱 Enviando resultados...")
                
                await update.message.reply_text(f"📊 **Análisis de {params['pilot']}**\n\n{summary}")
                
                for graph in graphs:
                    if os.path.exists(graph['path']):
                        with open(graph['path'], 'rb') as photo:
                            await update.message.reply_photo(
                                photo=photo,
                                caption=graph['description']
                            )
                
                await processing_msg.delete()
                
            except Exception as e:
                await processing_msg.edit_text(f"❌ Error generando análisis: {str(e)}")
                
        except Exception as e:
            await processing_msg.edit_text(f"❌ Error procesando solicitud: {str(e)}")
    
    def get_event_graphs(self, year, track, driver):
        """
        Gets graphs for an event from the database.
        
        Args:
            year: Event year
            track: Circuit name
            driver: Driver code
            
        Returns:
            List of dictionaries with graph information
            
        Functions:
        - Connects to database
        - Executes SQL query to get graphs
        - Formats results in list of dictionaries
        - Closes database connection
        """
        conn, cursor = get_db_connection()
        
        query = """
        SELECT g.graph_path, g.description, g.name
        FROM Graph g
        JOIN EventF1 e ON g.event_id = e.id
        WHERE e.season = ? AND e.gp = ? AND e.driver = ?
        """
        
        cursor.execute(query, (year, track, driver))
        results = cursor.fetchall()
        
        conn.close()
        
        return [{'path': row[0], 'description': row[1], 'name': row[2]} for row in results]
    
    def run(self):
        application = Application.builder().token(self.token).build()
        
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_f1_query))
        
        print("🚀 Bot iniciado...")
        application.run_polling()

if __name__ == "__main__":
    bot = F1TelegramBot()
    bot.run()