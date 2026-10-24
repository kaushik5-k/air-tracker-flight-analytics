import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px

st.set_page_config(
    page_title="Air Tracker",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Air Tracker: Flight Analytics")
st.caption("Flight data dashboard")

@st.cache_data(ttl=60)
def load_data():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password=st.secrets["mysql"]["password"],
        database="air_tracker"
    )

    try:
        flights = pd.read_sql("SELECT * FROM flights", conn)
        aircraft = pd.read_sql("SELECT * FROM aircraft", conn)
        airports = pd.read_sql("SELECT * FROM airports", conn)
    finally:
        conn.close()

    return flights, aircraft, airports


def find_column(df, candidates):
    for name in candidates:
        if name in df.columns:
            return name
    return None


try:
    flights, aircraft, airports = load_data()

    status_col = find_column(
        flights, ["flight_status", "status"]
    )
    airline_col = find_column(
        flights, ["airline", "airline_name"]
    )
    number_col = find_column(
        flights, ["flight_number", "number"]
    )
    dep_col = find_column(
        flights, ["departure_airport", "origin"]
    )
    arr_col = find_column(
        flights, ["arrival_airport", "destination"]
    )
    date_col = find_column(
        flights, ["departure_time", "scheduled_departure",
                  "arrival_time", "scheduled_arrival", "flight_date"]
    )

    # Homepage summary
    delayed_count = 0
    if status_col:
        delayed_count = flights[status_col].astype(
            str
        ).str.lower().eq("delayed").sum()

    delay_pct = (
        round(delayed_count / len(flights) * 100, 1)
        if len(flights) else 0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Flights", len(flights))
    c2.metric("Aircraft Records", len(aircraft))
    c3.metric("Airports", len(airports))
    c4.metric("Delayed Flights", f"{delay_pct}%")

    # Flight status
    st.subheader("📊 Flight Status")
    if status_col:
        status_data = (
            flights[status_col].fillna("Unknown")
            .value_counts().rename_axis("Status")
            .reset_index(name="Flights")
        )
        fig = px.pie(
            status_data, names="Status", values="Flights",
            title="Flights by Status"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Flight status column was not found.")

    # Airline chart
    st.subheader("✈️ Flights by Airline")
    if airline_col:
        airline_data = (
            flights.dropna(subset=[airline_col])
            .groupby(airline_col).size()
            .reset_index(name="Flights")
            .sort_values("Flights", ascending=False)
            .head(10)
        )
        fig = px.bar(
            airline_data, x=airline_col, y="Flights",
            title="Top 10 Airlines"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Search and filters
    st.subheader("🔎 Search and Filter Flights")
    filtered = flights.copy()

    search = st.text_input("Search by flight number or airline")
    if search:
        mask = pd.Series(False, index=filtered.index)
        for col in [number_col, airline_col]:
            if col:
                mask |= filtered[col].astype(str).str.contains(
                    search, case=False, na=False
                )
        filtered = filtered[mask]

    f1, f2 = st.columns(2)
    if status_col:
        statuses = sorted(
            flights[status_col].dropna().astype(str).unique()
        )
        selected_status = f1.multiselect(
            "Flight status", statuses
        )
        if selected_status:
            filtered = filtered[
                filtered[status_col].astype(str).isin(selected_status)
            ]

    if dep_col:
        origins = sorted(
            flights[dep_col].dropna().astype(str).unique()
        )
        selected_origins = f2.multiselect(
            "Origin airport", origins
        )
        if selected_origins:
            filtered = filtered[
                filtered[dep_col].astype(str).isin(selected_origins)
            ]

    st.caption(f"Showing {len(filtered)} matching flights")
    st.dataframe(filtered, use_container_width=True)

    # Airport details
    st.subheader("🛫 Airport Details Viewer")
    airport_code_col = find_column(
        airports, ["iata_code", "iata", "airport_code", "code"]
    )
    airport_name_col = find_column(
        airports, ["name", "airport_name"]
    )

    if airport_code_col:
        codes = sorted(
            airports[airport_code_col].dropna().astype(str).unique()
        )
        if codes:
            selected_airport = st.selectbox(
                "Select airport", codes
            )
            airport_info = airports[
                airports[airport_code_col].astype(str)
                == selected_airport
            ]
            st.dataframe(airport_info, use_container_width=True)

            if dep_col and arr_col:
                linked = flights[
                    flights[dep_col].astype(str).eq(selected_airport)
                    | flights[arr_col].astype(str).eq(selected_airport)
                ]
                st.write("Linked flights")
                st.dataframe(linked, use_container_width=True)
    else:
        st.info(
            "Airport code column was not recognized. "
            "Check the airports table column names."
        )
        st.dataframe(airports.head(20), use_container_width=True)

    # # Delay Analysis
    st.subheader("✈️ Delay Analysis by Airport")

    delay_data = flights.copy()
    delay_data["_delayed"] = (
        delay_data["flight_status"]
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("delayed")
   )

    
    
 

    delay_data = (
        delay_data.groupby("arrival_airport")
        .agg(
            Total_Flights=("flight_status", "size"),
            Delayed_Flights=("_delayed", "sum")
        )
        .reset_index()
    )

    delay_data["Delay_Percentage"] = (
        delay_data["Delayed_Flights"]
        .div(delay_data["Total_Flights"].replace(0, 1))
        .mul(100)
        .round(2)
    )

    delay_data = delay_data.sort_values(
        by="Delay_Percentage",
        ascending=False
    )

    fig = px.bar(
        delay_data,
        x="arrival_airport",
        y="Delay_Percentage",
        title="Delayed Flight Percentage by Airport",
        hover_data=["Total_Flights", "Delayed_Flights"]
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(delay_data, use_container_width=True)

    # Most delayed airports
    st.subheader("🏆 Most Delayed Airports")

    most_delayed = delay_data.sort_values(
        by="Delayed_Flights",
        ascending=False
    ).head(10)

    st.dataframe(most_delayed, use_container_width=True)

    

    # Full flight records
    st.subheader("📋 Flight Records")
    st.dataframe(flights, use_container_width=True)

except Exception as e:
    st.error(f"Dashboard error: {e}")