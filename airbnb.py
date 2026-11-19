"""
Nabil Handal
CS 230

Dataset: Inside Airbnb, Cambridge, MA listings, September 2026.
Purpose: Help visitors compare Airbnb nightly prices across Cambridge neighborhoods.
AI coding partner: ChatGPT.

"""
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st


DATA_FILE = Path(__file__).resolve().parent / "Data" / "airbnb" / "airbnb_camb_listings.csv"


@st.cache_data
def load_listings():
    listings = pd.read_csv(DATA_FILE)
    listings["price"] = pd.to_numeric(listings["price"], errors="coerce")
    listings["minimum_nights"] = pd.to_numeric(
        listings["minimum_nights"], errors="coerce"
    )

    #[STR_CLEAN] Method: AUGMENT.
    # I clean the text columns the app uses for dropdowns, the map, and the
    # results table. strip() removes spaces at the start and end, and
    # replace() turns runs of spaces inside the text into one space.
    # For example, "  Mid-Cambridge " becomes "Mid-Cambridge", so it does not
    # show up as a second, separate neighborhood in the dropdown.

    for column in ["neighbourhood", "room_type", "name"]:
        listings[column] = (
            listings[column].str.strip().str.replace(r"\s+", " ", regex=True)
        )
    return listings

st.set_page_config(page_title="Cambridge Airbnb Explorer", layout="wide")
st.title("Cambridge Airbnb Explorer")
st.write(
    "Compare nightly listing prices in Cambridge, Massachusetts. "
    "This first view helps you see which neighborhoods fit your budget."
)

#[INPUT_CHECK] Method: IDENTIFY & EXPLAIN.
# The try block loads the CSV file.
# If the file is missing, the app shows an error and stops.
# For example, if the CSV is not in the Data/airbnb folder,
# load_listings() raises FileNotFoundError, so the except block runs.

try:
    listings = load_listings()
except FileNotFoundError:
    st.error("Place airbnb_camb_listings.csv in the Data/airbnb folder next to this app.")
    st.stop()

st.header("1. Compare neighborhood prices")
room_types = sorted(listings["room_type"].dropna().unique())
neighborhoods = sorted(listings["neighbourhood"].dropna().unique())

room_type = st.selectbox("Room type", room_types)
selected_neighborhoods = st.multiselect(
    "Neighborhoods to compare",
    neighborhoods,
    default=neighborhoods,
)

#[INPUT_CHECK] Method: IDENTIFY & EXPLAIN.
# This checks whether the user selected any neighborhoods before filtering.
# Example: clearing every selection gives []. The condition is True, so the
# app shows a message and skips the else block containing the comparison.

if not selected_neighborhoods:
    st.info("Choose at least one neighborhood to see the comparison.")
else:
    matching = listings[
        (listings["room_type"] == room_type)
        & (listings["neighbourhood"].isin(selected_neighborhoods))
    ]
    priced = matching.dropna(subset=["price"])

#[INPUT_CHECK] Method: IDENTIFY & EXPLAIN.
# This checks whether any matching listings remain after missing prices
# are removed. Example: two matching rows both have missing prices.
# dropna() removes both rows, priced.empty is True, and a message appears
# instead of trying to build a price comparison from zero rows.
    
    if priced.empty:
        st.info("There are no priced listings for this room type and neighborhood selection.")
    else: 
        price_summary = (
            priced.groupby("neighbourhood")["price"]
            .agg(["mean", "count"])
            .sort_values("mean")
        )
        price_summary.columns = ["Average nightly price ($)", "Priced listings"]

        st.subheader(f"Average nightly price for {room_type.lower()} listings")
        st.bar_chart(
            price_summary.reset_index(),
            x="neighbourhood",
            y="Average nightly price ($)",
            x_label="Neighborhood",
            y_label="Average listed price per night (USD)",
            color="#267c89",
            horizontal=True,
            sort=False,
            height=max(350, len(price_summary) * 40),
        )

        st.dataframe(
            price_summary.style.format({"Average nightly price ($)": "${:,.0f}"}),
            use_container_width=True,
        )
        st.caption(
            f"Based on {len(priced):,} listings with a price. "
            f"{len(matching) - len(priced):,} matching listings have no price "
            "and are left out. A few expensive listings can raise an average. "
            "Prices are listing prices, not a confirmed total for your dates."
        )

st.header("2. Explore the price range")
st.write(
    "See how many listings fall into each $100 price group. "
    "The room type and neighborhoods selected above also apply here."
)

highest_price = int(listings["price"].max())
price_range = st.slider(
    "Nightly price range ($)",
    min_value=0,
    max_value=highest_price,
    value=(0, 1000),
    step=25,
)

if not selected_neighborhoods:
    st.info("Choose at least one neighborhood above to explore prices.")
else:
    in_range = priced[
        priced["price"].between(price_range[0], price_range[1])
    ].copy()
    
#[INPUT_CHECK] Method: IDENTIFY & EXPLAIN.
# This checks whether the selected price range contains any listings.
# Example: if the matching prices are $150 and $200 and the range is
# $0 to $100, in_range has zero rows. The app shows a message and skips
# the chart code in the else block.

    if in_range.empty:
        st.info("No priced listings match this room type, neighborhood, and price range.")
    else:
        # Put each price in a $100 group, such as $155 in the $100 to $199 group.
        in_range["price_band"] = (in_range["price"] // 100 * 100).astype(int)
        counts = in_range.groupby("price_band").size().sort_index()

#[LIST_COMP] Method: REVISE / REWRITE.
# This version separates counting, creating labels, and building the
# chart table into steps. The list comprehension makes one label for
# each price-band start in counts.index, keeping the code short.
# For start = 100, the formatted label is "$100 to $199".

        price_labels = [f"${start:,} to ${start + 99:,}" for start in counts.index]
        chart_data = pd.DataFrame({"Price range": price_labels, "Listings": counts.values})

        st.subheader(f"Price distribution for {room_type.lower()} listings")
        st.bar_chart(
            chart_data,
            x="Price range",
            y="Listings",
            x_label="Nightly price group (USD)",
            y_label="Number of listings",
            color="#cc714e",
            sort=False,
        )
        st.caption(
            f"{len(in_range):,} listings fall within your selected price range. "
            f"{len(matching) - len(priced):,} matching listings "
            "have no price and are left out. The chart counts listings, "
            "not bookings or available nights."
        )

st.header("3. Find listings for your visit")
st.write(
    "Choose your maximum nightly price and the length of your stay. "
    "The room type and neighborhoods selected above also apply here."
)
budget = st.slider("Maximum nightly budget ($)", 0, highest_price, 250, 25)
stay_nights = st.number_input("Number of nights", min_value=1, value=3, step=1)

if not selected_neighborhoods:
    st.info("Choose at least one neighborhood above to find listings.")
else:
    under_budget = priced[priced["price"] <= budget]
    choices = under_budget[under_budget["minimum_nights"] <= stay_nights].copy()
    choices["estimated_cost"] = choices["price"] * stay_nights
    choices = choices.sort_values("price")

#[INPUT_CHECK] Method: IDENTIFY & EXPLAIN.
# This checks whether any listings pass both the budget and stay filters.
# Example: a $150 listing passes a $200 budget, but its five-night minimum
# fails a three-night visit. If no other rows pass, choices.empty is True
# and the app suggests changing the budget or number of nights.

    if choices.empty:
        st.info("No listings match your budget and stay length. Try a higher budget or more nights.")
    else:
        st.write(f"{len(choices):,} listings match your choices.")
        map_listings = choices.dropna(subset=["latitude", "longitude"])


#[MANUAL_CALC] Method: AUGMENT.
# I added a price-range summary for the matching listings. My own loop
# finds the lowest and highest nightly price, then I compare the results
# with Pandas .min() and .max(). Both start at the first price, and each
# later price replaces lowest if it is smaller or highest if it is larger.
# Example: prices 120, 95, 210. lowest goes 120 -> 95, highest goes
# 120 -> 210, so the range is $95 to $210, the same as .min() and .max().

        match_prices = choices["price"].tolist()
        lowest = match_prices[0]
        highest = match_prices[0]
        for price in match_prices[1:]:
            if price < lowest:
                lowest = price
            if price > highest:
                highest = price

        if lowest == choices["price"].min() and highest == choices["price"].max():
            st.write(
                f"Nightly prices for your matches run from ${lowest:,.0f} to ${highest:,.0f}. "
                "My loop gives the same result as Pandas .min() and .max()."
            )
        else:
            st.warning("The loop result does not match Pandas .min() and .max().")
        map_listings = choices.dropna(subset=["latitude", "longitude"])


#[INPUT_CHECK] Method: IDENTIFY & EXPLAIN.
# The map uses only listings with both latitude and longitude.
# Example: if the only matching listing has no latitude, dropna()
# removes it from map_listings. This condition is False, so the app
# shows the no-coordinates message and still displays the results table.

        if not map_listings.empty:
            dots = pdk.Layer(
                "ScatterplotLayer",
                data=map_listings,
                get_position="[longitude, latitude]",
                get_fill_color=[38, 124, 137, 180],
                get_radius=70,
                pickable=True,
            )
            view = pdk.ViewState(
                latitude=map_listings["latitude"].mean(),
                longitude=map_listings["longitude"].mean(),
                zoom=12,
            )
            map_chart = pdk.Deck(
                layers=[dots],
                initial_view_state=view,
                tooltip={"text": "{name}\nNeighborhood: {neighbourhood}\nNightly price: ${price}\nMinimum stay: {minimum_nights} nights"},
            )
            st.pydeck_chart(map_chart)
        else:
            st.info("Matching listings have no map coordinates.")

        results = choices[["name", "neighbourhood", "room_type", "price", "minimum_nights", "estimated_cost"]]

#[DICT_DRIVEN] Method: AUGMENT.
# The column-label dictionary includes estimated_cost so the added
# stay-cost calculation has a clear heading with dollar units.
# Each key is an original column name and its value is the heading
# displayed in the table. For example, "estimated_cost" becomes
# "Estimated stay cost ($)". Renaming changes the labels, not the values.

        results = results.rename(columns={
            "name": "Listing",
            "neighbourhood": "Neighborhood",
            "room_type": "Room type",
            "price": "Nightly price ($)",
            "minimum_nights": "Minimum nights",
            "estimated_cost": "Estimated stay cost ($)",
        })
        st.dataframe(
            results.style.format({
                "Nightly price ($)": "${:,.0f}",
                "Minimum nights": "{:.0f}",
                "Estimated stay cost ($)": "${:,.0f}",
            }),
            hide_index=True,
            use_container_width=True,
        )
        st.caption(
            "A listing matches when its minimum stay is no longer than your visit. "
            "Estimated stay cost is nightly price multiplied by your number of nights, "
            "before fees and taxes. This does not confirm availability on your dates."
        )

        