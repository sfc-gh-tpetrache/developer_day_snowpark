import sys, os
sys.path.append(os.getcwd()+'/steps')

import streamlit as st
import numpy as np
import pandas as pd
import altair as alt
import pydeck as pdk
from datetime import datetime
import snowflake.snowpark as snp

# LOAD DATA ONCE
@st.experimental_singleton
def load_data():
    # establish a session with the Snowflake database.
    from snowpark_connection import snowpark_connect
    session, state_dict = snowpark_connect('./include/state.json')
    data = session.table("squirrels_engineered_features").to_pandas()
    data.columns = data.columns.str.strip().str.lower()
    return data

# FUNCTION FOR Central Park MAPS
def map(data, lat, lon, zoom):
    st.write(
        pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state={
                "latitude": lat,
                "longitude": lon,
                "zoom": zoom,
                "pitch": 50,
            },
            layers=[
                pdk.Layer(
                    "HexagonLayer",
                    data=data,
                    get_position=["lon", "lat"],
                    radius=100,
                    elevation_scale=4,
                    elevation_range=[0, 1000],
                    pickable=True,
                    extruded=True,
                ),
            ],
        )
    )

 
def color_map(data, lat, lon, zoom):
   
    data = data[data.primary_fur_color != 'Unknown'].copy()

    data['r'] = np.where(data.primary_fur_color == 'Gray', 128, (np.where(data.primary_fur_color == 'Black', 0, 210)))
    data['g'] = np.where(data.primary_fur_color == 'Gray', 128, (np.where(data.primary_fur_color == 'Black', 0, 105)))
    data['b'] = np.where(data.primary_fur_color == 'Gray', 128, (np.where(data.primary_fur_color == 'Black', 0, 30)))
    data['a'] = 100

    st.write(pdk.Deck(
     map_style='mapbox://styles/mapbox/light-v9',
     initial_view_state=pdk.ViewState(
         latitude=lat,
         longitude=lon,
         zoom=zoom,
         pitch=30,
     ),
     layers=[
         pdk.Layer(
             'ScatterplotLayer',
             data=data,
             get_position=["lon", "lat"],
             get_color=["r", "g", "b", "a"],
             get_radius=50,
         ),
     ],
 ))


# CALCULATE MIDPOINT FOR GIVEN SET OF DATA
@st.experimental_memo
def mpoint(lat, lon):
    return (np.average(lat), np.average(lon))


# FILTER DATA FOR A SPECIFIC DAY, CACHE
@st.experimental_memo
def filterdata(data, day_selected):
    map_data = (
        data.loc[data["date"] == day_selected]
        if day_selected != "All dates"
        else data
    )
    return map_data


# STREAMLIT APP LAYOUT

st.set_page_config(layout="wide")

data = load_data()

st.title("Central Park Squirrel Census")

st.write(
    f'If you’ve ever wondered how many squirrels live in New York City’s Central Park, there’s finally an answer:')

st.metric(label="Squirrel Population", value=str(len(data["unique_squirrel_id"].unique())))


st.write('That number comes from the first squirrel census of Manhattan’s largest park, '\
    'conducted by Jamie Allen and more than 300 volunteers who made it their mission to count'\
     'and observe the rodents living in the 843 acres of green space.')

# st.write(' > It immediately became comical to me. Squirrels are an animal that we interact with ' \
#    'on a daily basis, they’re disease-carrying, and they’re so common that we don’t even pay attention to them.')

st.markdown("""---""")
    
# FILTERS
date_selectbox = st.sidebar.selectbox(
    "Date", ["All dates"] + sorted(data["date"].unique())
)

shifts = st.sidebar.markdown("Day-shifts")
shift_am_checkbox = st.sidebar.checkbox("AM", True)
shift_pm_checkbox = st.sidebar.checkbox("PM", True)
checked_shifts = list()
if shift_am_checkbox:
    checked_shifts.append("AM")
if shift_pm_checkbox:
    checked_shifts.append("PM")


#st.map(data)
#st.map(filterdata(data, date_selectbox))

# LAYING OUT THE TOP SECTION OF THE APP - BAR CHARTS
row1_1, row1_2 = st.columns([1, 1])

with row1_1:
    """
    ### Time of squirrels sightings
    """

    date_counts = pd.DataFrame(data.groupby(["date", "shift"]).size()).reset_index()
    date_counts.columns = ["Date", "Shift", "Number of squirrel meetings"]
    date_chart = (
        alt.Chart(date_counts)
        .mark_bar()
        .encode(x=alt.X("Date"), y="Number of squirrel meetings", color="Shift")
        .properties(title="Squirrel meetings by date", width=400, height=400)
    )
    st.altair_chart(date_chart)
    st.write(
    f'Squirrels were seen more in the afternoons - '
    f'{len(data.loc[data["shift"] == "PM"])} times. In the morning shifts researchers '
    f'have met the squirrels {len(data.loc[data["shift"] == "AM"])} times.'
)


with row1_2:

    """
    ### Squirrel Population by Age Group
    """
    data["age"].replace("?", "Unknown", inplace=True)
    age_counts = data["age"].value_counts().reset_index()

    age_chart = (
        alt.Chart(age_counts)
        .mark_bar()
        .encode(x="age", y="index")
        .properties(title="Squirrels by age", width=400, height=400)
    )

    st.altair_chart(age_chart)
    st.write(
        "It is difficult to define squirrel age, just by looking at it. "
        "This is the reason of a lot of unknown values."
    )

# LAYING OUT THE MIDDLE SECTION OF THE APP - SOUNDS
row2_1, row2_2 = st.columns([1, 1])

with row2_1:
    """
    ### What are NYC Squirrels Doing?
    """
    activity_data = (
    data[["running", "chasing", "climbing", "eating", "foraging"]].sum().reset_index()
    )
    activity_data.columns = ["Activity", "Count"]
    activity_chart = (
        alt.Chart(activity_data)
        .mark_bar()
        .encode(x=alt.X("Activity:O"), y=alt.Y("Count:Q", sort='x'))
        .properties(height=400, width=400)
    )
    st.altair_chart(activity_chart)

    st.write("Squirrels in Central Park were a hungry bunch - " \
    "the top two activities that they were recorded doing was foraging and eating.")


with row2_2:
    """
    ### NYC Squirrel Behavior Towards Humans
    """
    behaviour_data = (
    data[["approaches", "indifferent", "runs_from"]].sum().reset_index()
    )
    behaviour_data.columns = ["Behaviour", "Count"]
    behaviour_data = (
        alt.Chart(behaviour_data)
        .mark_bar()
        .encode(x="Behaviour:O", y="Count:Q")
        .properties(height=400, width=400)
    )
    st.altair_chart(behaviour_data)

    st.write("What we do know is that not many squirrels approached humans, more ran from humans  " \
         "and most of them were indifferent from humans.")


# MAP AREA - SETTING THE ZOOM LOCATIONS 
central_park = [40.785, 73.968]
zoom_level = 12
midpoint = mpoint(data["lat"], data["lon"])

# LAYING OUT THE TOP SECTION OF THE APP
row3_1, row3_2 = st.columns([1, 1])

# filter by shift
data = data.loc[data["shift"].isin(checked_shifts)]

with row3_1:
    """
    ### Map of squirrels sightings
    """
    map(filterdata(data, date_selectbox), midpoint[0], midpoint[1], zoom_level)
   
        
with row3_2:
    """
    ### Color coded map of fur
    """
    color_map(filterdata(data, date_selectbox), midpoint[0], midpoint[1], zoom_level)


if st.checkbox("Show Raw Data"):
    st.dataframe(filterdata(data, date_selectbox).head(20))
