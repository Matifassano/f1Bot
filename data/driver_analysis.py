import os
import sys
import seaborn as sns
import numpy as np
import pandas as pd
from pandas import to_timedelta
import fastf1
import fastf1.plotting
from fastf1.core import Laps
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
from timple.timedelta import strftimedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) ##Add the base directory to the path to fix the import error
sys.path.append(BASE_DIR)
from db.dbHandler import get_db_connection

fastf1.plotting.setup_mpl(mpl_timedelta_support=True, misc_mpl_mods=False, color_scheme='fastf1') ##Dark mode

driver_number = '43'
driver_name = 'COL'
team_name = ["Alpine", "Williams"]
teammates_names = ["GAS", "ALB"]
teammates_numbers = ["10", "23"]

conn, cursor = get_db_connection()


## Get the event data from the database
def get_event_data(year, track, driver):
    query = "SELECT id FROM EventF1 WHERE season = ? AND gp = ? AND driver = ?"
    cursor.execute(query, (year, track, driver))
    result = cursor.fetchall()
    return result

## Get the graph data from the database
def get_graph_data(event_id, name):
    query = "SELECT id FROM Graph WHERE event_id = ? AND name = ?"
    cursor.execute(query, (event_id, name))
    result = cursor.fetchall()
    return result

## Data functions
def race_positions_changes(year, track, driverNum): ##Driver Number
    event_data = get_event_data(year, track, driver_name)
    
    if event_data:
        # If event exists, check if graph exists
        graph_data = get_graph_data(event_data[0][0], 'race_positions_changes')
        if graph_data:
            print(f"Graph (race_positions_changes) already exists for {driver_name} in {year} {track}")
            return graph_data[0]
        else:
            print(f"Event exists but graph (race_positions_changes) does not exist, creating graph...")
            event_id = event_data[0][0]  # Usar el event_id existente

    print(f"Event does not exist for {driver_name} in {year} {track}, creating event...")

    race = fastf1.get_session(year, track, 'R')
    race.load(telemetry=False, weather=False)
    fig, ax = plt.subplots(figsize=(8.0, 4.9))

    for drv in race.drivers:
        drv_laps = race.laps.pick_drivers(drv)
        abb = drv_laps['Driver'].iloc[0]
        style = fastf1.plotting.get_driver_style(identifier=abb, style=['color', 'linestyle'], session=race)
        if drv != driverNum:
            style['color'] = 'blue'
            style['linestyle'] = '-'
        ax.plot(drv_laps['LapNumber'], drv_laps['Position'], label=abb, **style)

    ax.set_ylim([20.5, 0.5])
    ax.set_yticks([1, 5, 10, 15, 20])
    ax.set_xlabel('Lap')
    ax.set_ylabel('Position')
    ax.legend(bbox_to_anchor=(1.0, 1.02))

    filename = f"race_positions_changes_{driver_name}_{track}_{year}.png"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, "media", filename)

    drv_laps = race.laps.pick_drivers(driverNum)
    description = f"{driver_name} driver started in position {drv_laps['Position'].iloc[0]} and finished in position {drv_laps['Position'].iloc[-1]}"

    # Solo insertar evento si no existe
    if not event_data:
        query = """
        INSERT INTO EventF1 (season, gp, driver) 
        OUTPUT INSERTED.id
        VALUES (?, ?, ?)
        """
        cursor.execute(query, (year, track, driver_name))
        event_id = int(cursor.fetchone()[0])
        conn.commit()

    query = """
    INSERT INTO Graph (event_id, name, graph_path, description) 
    OUTPUT INSERTED.id
    VALUES (?, ?, ?, ?)
    """
    cursor.execute(query, (event_id, 'race_positions_changes', filepath, description))
    graph_id = int(cursor.fetchone()[0])
    conn.commit()

    plt.savefig(filepath)
    plt.close(fig)
    print(f"Graph (race_positions_changes) created for {driver_name} in {year} {track}")
    return graph_id
        

def race_laps_times(year, track, driver): ##Driver name

    event_data = get_event_data(year, track, driver)
    if event_data:
        graph_data = get_graph_data(event_data[0][0], 'race_laps_times')
        if graph_data:
            print(f"Graph (race_laps_times) already exists for {driver} in {year} {track}")
            return graph_data[0]
        else:
            print(f"Event exists but graph (race_laps_times) does not exist, creating graph...")
            event_id = event_data[0][0]

    print(f"Event does not exist for {driver} in {year} {track}, creating event...")
    race = fastf1.get_session(year, track, 'R')
    race.load()
    driver_laps = race.laps.pick_drivers(driver).pick_quicklaps().reset_index()
    fig, ax = plt.subplots(figsize=(8, 8))

    # Scatterplot of lap times
    sns.scatterplot(
        data=driver_laps,
        x="LapNumber",
        y="LapTime",
        ax=ax,
        hue="Compound",
        palette=fastf1.plotting.get_compound_mapping(session=race),
        s=80,
        linewidth=0,
        legend='auto'
    )
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time")

    # Add trend line
    lap_numbers = driver_laps["LapNumber"].values
    lap_times_sec = driver_laps["LapTime"].dt.total_seconds().values

    # Only fit if there are enough laps
    if len(lap_numbers) > 20:
        # Fit a 1st degree polynomial (linear trend)
        z = np.polyfit(lap_numbers, lap_times_sec, 1)
        p = np.poly1d(z)
        trend_lap_times_sec = p(lap_numbers)
        # Convert back to timedelta for plotting
        trend_lap_times = to_timedelta(trend_lap_times_sec, unit='s')
        ax.plot(
            lap_numbers,
            trend_lap_times,
            color='white',
            linestyle='--',
            linewidth=2,
        )
        # Add trend line to legend
        handles, labels = ax.get_legend_handles_labels()

    # The y-axis increases from bottom to top by default
    # Since we are plotting time, it makes sense to invert the axis
    ax.invert_yaxis()
    plt.suptitle(f"{driver} Laptimes in the {year} {track} Grand Prix")

    # Turn on major grid lines
    plt.grid(color='w', which='major', axis='both')
    sns.despine(left=True, bottom=True)

    filename = f"race_laps_times_{driver}_{track}_{year}.png"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, "media", filename)
    description = f"{driver} driver lap times in the {year} {track} Grand Prix"

    # Solo insertar evento si no existe
    if not event_data:
        query = """
        INSERT INTO EventF1 (season, gp, driver) 
        OUTPUT INSERTED.id
        VALUES (?, ?, ?)
        """
        cursor.execute(query, (year, track, driver))
        event_id = int(cursor.fetchone()[0])
        conn.commit()

    query = """
    INSERT INTO Graph (event_id, name, graph_path, description) 
    OUTPUT INSERTED.id
    VALUES (?, ?, ?, ?)
    """
    cursor.execute(query, (event_id, 'race_laps_times', filepath, description))
    graph_id = int(cursor.fetchone()[0])
    conn.commit()

    plt.savefig(filepath)
    plt.close(fig)
    print(f"Graph (race_laps_times) created for {driver} in {year} {track}")
    return graph_id

##def time_race_pace(year, track):

    event_data = get_event_data(year, track, driver)
    if event_data:
        graph_data = get_graph_data(event_data[0][0], 'time_race_pace')
        if graph_data:
            print(f"Graph (time_race_pace) already exists for {driver} in {year} {track}")
            return graph_data[0]
        else:
            print(f"Event exists but graph (time_race_pace) does not exist, creating graph...")
            event_id = event_data[0][0]

    print(f"Event does not exist for {driver} in {year} {track}, creating event...")
    race = fastf1.get_session(year, track, 'R')
    race.load()
    laps = race.laps.pick_quicklaps()

    transformed_laps = laps.copy()
    transformed_laps.loc[:, "LapTime (s)"] = laps["LapTime"].dt.total_seconds()

    # order the team from the fastest (lowest median lap time) tp slower
    team_order = (
        transformed_laps[["Team", "LapTime (s)"]]
        .groupby("Team")
        .median()["LapTime (s)"]
        .sort_values()
        .index
    )
    print(team_order)

    # make a color palette associating team names to hex codes
    team_palette = {team: fastf1.plotting.get_team_color(team, session=race)
                    for team in team_order}

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.boxplot(
        data=transformed_laps,
        x="Team",
        y="LapTime (s)",
        hue="Team",
        order=team_order,
        palette=team_palette,
        whiskerprops=dict(color="white"),
        boxprops=dict(edgecolor="white"),
        medianprops=dict(color="grey"),
        capprops=dict(color="white"),
    )

    plt.title(f"{year} {track} Grand Prix")
    plt.grid(visible=False)

    # x-label is redundant
    ax.set(xlabel=None)
    plt.tight_layout()
    plt.show()

def race_laptimes_distribution(year, track, driverNum): ##Driver number
    event_data = get_event_data(year, track, driver_name)
    if event_data:
        graph_data = get_graph_data(event_data[0][0], 'race_laptimes_distribution')
        if graph_data:
            print(f"Graph (race_laptimes_distribution) already exists for {driver_name} in {year} {track}")
            return graph_data[0]
        else:
            print(f"Event exists but graph (race_laptimes_distribution) does not exist, creating graph...")
            event_id = event_data[0][0]

    print(f"Event does not exist for {driver_name} in {year} {track}, creating event...")
    race = fastf1.get_session(year, track, 'R')
    race.load()

    point_finishers = race.drivers[:10]
    if driverNum not in point_finishers:
        point_finishers.append(driverNum)
    print(point_finishers)
    driver_laps = race.laps.pick_drivers(point_finishers).pick_quicklaps()
    driver_laps = driver_laps.reset_index()

    finishing_order = [race.get_driver(i)["Abbreviation"] for i in point_finishers]
    print(finishing_order)

    fig, ax = plt.subplots(figsize=(10, 5))

    driver_laps["LapTime(s)"] = driver_laps["LapTime"].dt.total_seconds()

    sns.violinplot(data=driver_laps,
                x="Driver",
                y="LapTime(s)",
                hue="Driver",
                inner=None,
                density_norm="area",
                order=finishing_order,
                palette=fastf1.plotting.get_driver_color_mapping(session=race)
                )

    sns.swarmplot(data=driver_laps,
                x="Driver",
                y="LapTime(s)",
                order=finishing_order,
                hue="Compound",
                palette=fastf1.plotting.get_compound_mapping(session=race),
                hue_order=["SOFT", "MEDIUM", "HARD"],
                linewidth=0,
                size=4,
                )

    ax.set_xlabel("Driver")
    ax.set_ylabel("Lap Time (s)")
    plt.suptitle(f"{year} {track} Grand Prix Lap Time Distributions")
    sns.despine(left=True, bottom=True)

    filename = f"race_laptimes_distribution_{driver_name}_{track}_{year}.png"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, "media", filename)
    description = f"{driver_name} driver lap time distribution in the {year} {track} Grand Prix"

    if not event_data:
        query = """
        INSERT INTO EventF1 (season, gp, driver) 
        OUTPUT INSERTED.id
        VALUES (?, ?, ?)
        """
        cursor.execute(query, (year, track, driver_name))
        event_id = int(cursor.fetchone()[0])
        conn.commit()

    query = """
    INSERT INTO Graph (event_id, name, graph_path, description) 
    OUTPUT INSERTED.id
    VALUES (?, ?, ?, ?)
    """
    cursor.execute(query, (event_id, 'race_laptimes_distribution', filepath, description))
    graph_id = int(cursor.fetchone()[0])
    conn.commit()

    plt.savefig(filepath)
    plt.close(fig)
    print(f"Graph (race_laptimes_distribution) created for {driver_name} in {year} {track}")
    return graph_id

def qualy_results(year, track, driver): ##Driver name
    event_data = get_event_data(year, track, driver)
    if event_data:
        graph_data = get_graph_data(event_data[0][0], 'qualy_results')
        if graph_data:
            print(f"Graph (qualy_results) already exists for {driver} in {year} {track}")
            return graph_data[0]
        else:
            print(f"Event exists but graph (qualy_results) does not exist, creating graph...")
            event_id = event_data[0][0]

    print(f"Event does not exist for {driver} in {year} {track}, creating event...")
    
    session = fastf1.get_session(year, track, 'Q')
    session.load()

    drivers = pd.unique(session.laps['Driver'])
    print(drivers)

    list_fastest_laps = list()
    for drv in drivers:
        drvs_fastest_lap = session.laps.pick_drivers(drv).pick_fastest()
        if drvs_fastest_lap is not None:  # ✅ Solo agregar si no es None
            list_fastest_laps.append(drvs_fastest_lap)

    fastest_laps = Laps(list_fastest_laps) \
        .sort_values(by='LapTime') \
        .reset_index(drop=True)

    pole_lap = fastest_laps.pick_fastest()
    fastest_laps['LapTimeDelta'] = fastest_laps['LapTime'] - pole_lap['LapTime']

    team_colors = list()
    fig, ax = plt.subplots()
    for index, lap in fastest_laps.iterlaps():
        if lap['Driver'] == driver:
            color = fastf1.plotting.get_driver_color(lap['Driver'], session=session)

            ax.barh(index, lap['LapTimeDelta'], color=color, edgecolor='black', hatch='//', zorder=3)
            continue
        else:
            color = fastf1.plotting.get_team_color(lap['Team'], session=session)
        team_colors.append(color)

    ax.barh(fastest_laps.index, fastest_laps['LapTimeDelta'],
            color=team_colors, edgecolor='grey')
    ax.set_yticks(fastest_laps.index)
    ax.set_yticklabels(fastest_laps['Driver'])
    ax.invert_yaxis()

    ax.set_axisbelow(True)
    ax.xaxis.grid(True, which='major', linestyle='--', color='black', zorder=-1000)

    lap_time_string = strftimedelta(pole_lap['LapTime'], '%m:%s.%ms')

    plt.suptitle(f"{session.event['EventName']} {session.event.year} Qualifying\n"
                f"Fastest Lap: {lap_time_string} ({pole_lap['Driver']})")
    
    filename = f"qualy_results_{driver}_{track}_{year}.png"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    media_dir = os.path.join(script_dir, "media")
    os.makedirs(media_dir, exist_ok=True)
    filepath = os.path.join(media_dir, filename)
    description = f"{driver} driver qualy results in the {year} {track} Grand Prix."
    
    print(description)
    if not event_data:
        query = """
        INSERT INTO EventF1 (season, gp, driver) 
        OUTPUT INSERTED.id
        VALUES (?, ?, ?)
        """
        cursor.execute(query, (year, track, driver))
        event_id = int(cursor.fetchone()[0])
        conn.commit()

    query = """
    INSERT INTO Graph (event_id, name, graph_path, description) 
    OUTPUT INSERTED.id
    VALUES (?, ?, ?, ?)
    """
    cursor.execute(query, (event_id, 'qualy_results', filepath, description))
    graph_id = int(cursor.fetchone()[0])
    conn.commit()

    plt.savefig(filepath)
    plt.close(fig)
    print(f"Graph (qualy_results) created for {driver} in {year} {track}")
    return graph_id

##race_positions_changes(2025, 'Monaco', driver_number)
##race_laps_times(2025, 'Monaco', driver_name)
## time_race_pace(2025, 'Monaco')
##race_laptimes_distribution(2025, 'Monaco', driver_number)
qualy_results(2025, 'Imola', driver_name)