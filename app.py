import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
import requests

st.set_page_config(page_title="Air Tracker: Flight Analytics", page_icon="✈️", layout="wide")
st.title("✈️ Air Tracker: Flight Analytics")
st.write("Flight data dashboard")


def db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=st.secrets["mysql"]["password"],
        database="air_tracker"
    )


@st.cache_data(ttl=60)
def load_data():
    conn = db_connection()
    try:
        flights = pd.read_sql("SELECT * FROM flights", conn)
        aircraft = pd.read_sql("SELECT * FROM aircraft", conn)
        airports = pd.read_sql("SELECT * FROM airports", conn)
    finally:
        conn.close()
    return flights, aircraft, airports


def api_headers():
    return {
        "x-rapidapi-key": st.secrets["rapidapi"]["key"],
        "x-rapidapi-host": st.secrets["rapidapi"]["host"]
    }


def test_aerodatabox_api():
    url = "https://aerodatabox.p.rapidapi.com/airports/iata/DEL"
    try:
        response = requests.get(url, headers=api_headers(), timeout=20)
        if response.status_code == 200:
            return response.json()
        st.error(f"API Error: HTTP {response.status_code}")
        st.code(response.text)
    except (requests.RequestException, KeyError) as e:
        st.error(f"API connection/configuration failed: {e}")
    return None


if st.sidebar.button("Test AeroDataBox API"):
    api_test_data = test_aerodatabox_api()
    if api_test_data is not None:
        st.sidebar.success("API Connected Successfully!")
        st.sidebar.json(api_test_data)


def get_live_flights(airport_code="DEL"):
    url = f"https://aerodatabox.p.rapidapi.com/flights/airports/iata/{airport_code}"
    params = {"offsetMinutes": -120, "durationMinutes": 720, "direction": "Both"}
    try:
        response = requests.get(url, headers=api_headers(), params=params, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, dict):
                return result
            st.error("Unexpected API response format.")
            st.json(result)
        else:
            st.error(f"Live API Error: HTTP {response.status_code}")
            st.code(response.text)
    except (requests.RequestException, KeyError) as e:
        st.error(f"Live API connection/configuration failed: {e}")
    return None


def show_live_flights(data):
    if not isinstance(data, dict):
        st.warning("Unexpected API response format.")
        st.json(data)
        return

    arrivals = data.get("arrivals") or []
    departures = data.get("departures") or []
    col1, col2 = st.columns(2)
    col1.metric("Live Arrivals", len(arrivals))
    col2.metric("Live Departures", len(departures))

    def make_table(records):
        rows = []
        for flight in records:
            if not isinstance(flight, dict):
                continue
            airline = flight.get("airline") or {}
            aircraft_info = flight.get("aircraft") or {}
            movement = flight.get("movement") or {}
            rows.append({
                "Flight Number": flight.get("number") or flight.get("callSign") or "Unknown",
                "Airline": airline.get("name") or "Unknown",
                "Status": movement.get("status") or flight.get("status") or "Unknown",
                "Aircraft": aircraft_info.get("model") or "Unknown"
            })
        return pd.DataFrame(rows)

    st.subheader("🛬 Live Arrivals")
    arrivals_df = make_table(arrivals)
    if not arrivals_df.empty:
        st.dataframe(arrivals_df, use_container_width=True, hide_index=True)
    else:
        st.info("No arrival records returned.")

    st.subheader("🛫 Live Departures")
    departures_df = make_table(departures)
    if not departures_df.empty:
        st.dataframe(departures_df, use_container_width=True, hide_index=True)
    else:
        st.info("No departure records returned.")

    with st.expander("View raw API response"):
        st.json(data)


def ensure_live_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS live_flights (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            flight_number VARCHAR(50) NOT NULL,
            airline VARCHAR(255),
            direction VARCHAR(20) NOT NULL,
            airport_code VARCHAR(10) NOT NULL,
            flight_status VARCHAR(100),
            aircraft_model VARCHAR(255),
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_live_flight (flight_number, direction, airport_code)
        )
    """)


def save_live_flights(data, airport_code):
    if not isinstance(data, dict):
        st.error("No valid live data is available. Fetch live flights first.")
        return 0

    records = []
    for direction in ("Arrival", "Departure"):
        key = "arrivals" if direction == "Arrival" else "departures"
        for flight in data.get(key, []) or []:
            if not isinstance(flight, dict):
                continue
            airline_info = flight.get("airline") or {}
            aircraft_info = flight.get("aircraft") or {}
            movement = flight.get("movement") or {}
            flight_number = flight.get("number") or flight.get("callSign")
            if not flight_number:
                continue
            records.append((
                str(flight_number)[:50],
                str(airline_info.get("name") or "Unknown")[:255],
                direction,
                airport_code,
                str(movement.get("status") or flight.get("status") or "Unknown")[:100],
                str(aircraft_info.get("model") or "Unknown")[:255]
            ))

    if not records:
        st.warning("No live flight records to save.")
        return 0

    conn = None
    cursor = None
    try:
        conn = db_connection()
        cursor = conn.cursor()
        ensure_live_table(cursor)
        cursor.executemany("""
            INSERT INTO live_flights
                (flight_number, airline, direction, airport_code, flight_status, aircraft_model)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                airline = VALUES(airline),
                flight_status = VALUES(flight_status),
                aircraft_model = VALUES(aircraft_model),
                fetched_at = CURRENT_TIMESTAMP
        """, records)
        conn.commit()
        return len(records)
    except mysql.connector.Error as e:
        if conn is not None:
            conn.rollback()
        st.error(f"MySQL save error: {e}")
        return 0
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


# ---------------- LIVE FLIGHTS SECTION ----------------
st.divider()
st.header("🌐 Live Arrivals & Departures")
live_airport = st.selectbox(
    "Choose airport for live flights",
    ["DEL", "IXR", "BOM"],
    format_func=lambda code: {"DEL": "Delhi (DEL)", "IXR": "Ranchi (IXR)", "BOM": "Mumbai (BOM)"}[code],
    key="live_airport_select"
)

if "live_flight_data" not in st.session_state:
    st.session_state.live_flight_data = None
if "live_flight_airport" not in st.session_state:
    st.session_state.live_flight_airport = None

if st.button("Fetch Live Arrivals & Departures"):
    with st.spinner("Fetching live flight data..."):
        fetched_data = get_live_flights(live_airport)
    st.session_state.live_flight_data = fetched_data
    st.session_state.live_flight_airport = live_airport if fetched_data is not None else None

if st.session_state.live_flight_data is not None:
    st.success("API response received.")
    show_live_flights(st.session_state.live_flight_data)
    if st.button("Save Live Data to MySQL"):
        saved_count = save_live_flights(
            st.session_state.live_flight_data,
            st.session_state.live_flight_airport
        )
        if saved_count:
            st.success(f"{saved_count} live flight records processed in MySQL.")
        else:
            st.warning("No records were saved. Check the error message above.")


def find_column(df, candidates):
    columns = {str(col).lower().strip(): col for col in df.columns}
    for name in candidates:
        key = name.lower().strip()
        if key in columns:
            return columns[key]
    return None


# ---------------- MAIN DASHBOARD ----------------
try:
    flights, aircraft, airports = load_data()
    if flights.empty:
        st.warning("No flight records found in the database.")
        st.stop()

    status_col = find_column(flights, ["flight_status", "status"])
    airline_col = find_column(flights, ["airline", "airline_name", "carrier"])
    number_col = find_column(flights, ["flight_number", "flight_no", "number"])
    dep_col = find_column(flights, ["departure_airport", "origin", "origin_airport"])
    arr_col = find_column(flights, ["arrival_airport", "destination", "destination_airport"])

    total_flights, total_aircraft, total_airports = len(flights), len(aircraft), len(airports)
    delayed_count = 0
    if status_col:
        delayed_count = flights[status_col].astype(str).str.strip().str.lower().eq("delayed").sum()
    delay_percentage = delayed_count / total_flights * 100 if total_flights else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Flights", f"{total_flights:,}")
    col2.metric("Aircraft Records", f"{total_aircraft:,}")
    col3.metric("Airports", f"{total_airports:,}")
    col4.metric("Delayed Flights", f"{delay_percentage:.1f}%")

    st.divider()
    st.subheader("📊 Flight Status")
    if status_col:
        status_data = flights[status_col].fillna("Unknown").astype(str).value_counts().rename_axis("Status").reset_index(name="Flights")
        st.plotly_chart(px.pie(status_data, names="Status", values="Flights", title="Flights by Status", hole=0.35), use_container_width=True)
    else:
        st.info("Flight status column was not found.")

    st.subheader("✈️ Top 10 Airlines")
    if airline_col:
        airline_data = flights[airline_col].fillna("Unknown").astype(str).value_counts().head(10).rename_axis("Airline").reset_index(name="Flights")
        st.plotly_chart(px.bar(airline_data, x="Airline", y="Flights", title="Flights by Airline", text="Flights"), use_container_width=True)
    else:
        st.info("Airline column was not found.")

    st.divider()
    st.subheader("🔎 Search and Filter Flights")
    search_text = st.text_input("Search by flight number or airline")
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        status_options = ["All"]
        if status_col:
            status_options += sorted(flights[status_col].dropna().astype(str).unique().tolist())
        selected_status = st.selectbox("Flight Status", status_options)
    with filter_col2:
        airport_options = ["All"]
        if dep_col:
            airport_options += sorted(flights[dep_col].dropna().astype(str).unique().tolist())
        selected_airport = st.selectbox("Origin Airport", airport_options)

    filtered_flights = flights.copy()
    if search_text.strip():
        search_columns = [col for col in [number_col, airline_col] if col is not None]
        if search_columns:
            mask = pd.Series(False, index=filtered_flights.index)
            for col in search_columns:
                mask |= filtered_flights[col].astype(str).str.contains(search_text.strip(), case=False, na=False, regex=False)
            filtered_flights = filtered_flights[mask]
    if status_col and selected_status != "All":
        filtered_flights = filtered_flights[filtered_flights[status_col].astype(str) == selected_status]
    if dep_col and selected_airport != "All":
        filtered_flights = filtered_flights[filtered_flights[dep_col].astype(str) == selected_airport]
    st.write(f"Showing {len(filtered_flights):,} matching flights")
    st.dataframe(filtered_flights, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("🛫 Airport Details")
    airport_code_col = find_column(airports, ["iata_code", "airport_code", "code"])
    airport_name_col = find_column(airports, ["airport_name", "name"])
    city_col = find_column(airports, ["city"])
    country_col = find_column(airports, ["country"])
    if not airports.empty and airport_code_col:
        airport_codes = airports[airport_code_col].dropna().astype(str).unique().tolist()
        if airport_codes:
            selected_code = st.selectbox("Select Airport", sorted(airport_codes))
            selected_rows = airports[airports[airport_code_col].astype(str) == selected_code]
            if not selected_rows.empty:
                airport = selected_rows.iloc[0]
                a1, a2, a3 = st.columns(3)
                a1.metric("Airport Code", str(airport[airport_code_col]))
                a2.metric("Airport Name", str(airport[airport_name_col]) if airport_name_col else "N/A")
                a3.metric("City", str(airport[city_col]) if city_col else "N/A")
                if country_col:
                    st.write("**Country:**", airport[country_col])
                if dep_col:
                    count = (flights[dep_col].astype(str) == selected_code).sum()
                    st.write(f"**Flights departing from this airport:** {count}")
                if arr_col:
                    count = (flights[arr_col].astype(str) == selected_code).sum()
                    st.write(f"**Flights arriving at this airport:** {count}")
    else:
        st.info("Airport code column was not found. Showing airport records below.")
        st.dataframe(airports, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("⏱️ Delay Analysis by Airport")
    if status_col and arr_col:
        delay_data = flights.copy()
        delay_data["_status"] = delay_data[status_col].fillna("").astype(str).str.strip().str.lower()
        delay_data["_arrival_airport"] = delay_data[arr_col].fillna("Unknown").astype(str)
        delay_data = delay_data.groupby("_arrival_airport").agg(
            Total_Flights=("_status", "size"),
            Delayed_Flights=("_status", lambda s: (s == "delayed").sum())
        ).reset_index().rename(columns={"_arrival_airport": "Arrival Airport"})
        delay_data["Delay_Percentage"] = (delay_data["Delayed_Flights"] / delay_data["Total_Flights"].replace(0, pd.NA) * 100).fillna(0)
        delay_data = delay_data.sort_values("Delay_Percentage", ascending=False)
        if not delay_data.empty:
            fig_delay = px.bar(
                delay_data, x="Arrival Airport", y="Delay_Percentage",
                title="Delayed Flight Percentage by Destination Airport",
                hover_data=["Total_Flights", "Delayed_Flights"],
                labels={"Delay_Percentage": "Delayed Flights (%)"}
            )
            st.plotly_chart(fig_delay, use_container_width=True)
            st.dataframe(delay_data, use_container_width=True, hide_index=True)
    else:
        st.info("Delay analysis needs arrival airport and flight status columns.")
        st.write("Available flight columns:", flights.columns.tolist())

    st.divider()
    st.subheader("🛣️ Top 10 Busiest Routes")
    if dep_col and arr_col:
        route_data = flights.groupby([dep_col, arr_col]).size().reset_index(name="Flights").sort_values("Flights", ascending=False).head(10)
        route_data["Route"] = route_data[dep_col].astype(str) + " → " + route_data[arr_col].astype(str)
        st.plotly_chart(px.bar(route_data, x="Route", y="Flights", title="Top 10 Busiest Routes", text="Flights"), use_container_width=True)
        st.dataframe(route_data, use_container_width=True, hide_index=True)
    else:
        st.info("Route analysis needs departure and arrival airport columns.")

    st.divider()
    st.subheader("📋 All Flight Records")
    st.dataframe(flights, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("✈️ Aircraft Details")
    st.write(f"Total Aircraft: {len(aircraft)}")
    if not aircraft.empty:
        st.dataframe(aircraft, use_container_width=True, hide_index=True)
    else:
        st.info("No aircraft records found.")

except Exception as e:
    st.error(f"Dashboard error: {e}")
    st.info("Check MySQL connection, database credentials, and table names.")