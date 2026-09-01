"""Avocado Prices & Volume Dashboard.

A Dash app exploring the Hass Avocado Board dataset (2015-2023): prices,
sales volume and bag-size mix across US regions, split by conventional
vs. organic avocados.
"""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

# ---------------------------------------------------------------------------
# Data loading & prep
# ---------------------------------------------------------------------------

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "avocado.csv")

# Rollup regions in this dataset (national + multi-state) that double-count
# volume already reported under individual metro regions.
AGGREGATE_REGIONS = {
    "TotalUS",
    "California",
    "GreatLakes",
    "Midsouth",
    "Northeast",
    "NorthernNewEngland",
    "Plains",
    "SouthCentral",
    "Southeast",
    "West",
}


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df = df.rename(columns={"smal_bags": "small_bags"})  # fix upstream typo
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")
    df["type"] = df["type"].str.capitalize()
    df["is_aggregate"] = df["region"].isin(AGGREGATE_REGIONS)
    df["year"] = df["date"].dt.year
    return df


df = load_data()

MIN_DATE = df["date"].min()
MAX_DATE = df["date"].max()
ALL_REGIONS = sorted(df["region"].unique())
ALL_TYPES = sorted(df["type"].unique())

TYPE_COLORS = {"Conventional": "#3E7C59", "Organic": "#C97B2C"}

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = Dash(__name__, title="Avocado Dashboard")
server = app.server  # exposed for gunicorn / Render


def kpi_card(card_id: str, label: str) -> html.Div:
    return html.Div(
        className="kpi-card",
        children=[
            html.Div(label, className="kpi-label"),
            html.Div(id=card_id, className="kpi-value"),
        ],
    )


app.layout = html.Div(
    className="app-container",
    children=[
        html.Header(
            className="app-header",
            children=[
                html.Div("🥑", className="header-emoji"),
                html.Div(
                    [
                        html.H1("Avocado Market Dashboard"),
                        html.P(
                            "US retail prices & volume, 2015–2023 "
                            "(Hass Avocado Board data)"
                        ),
                    ]
                ),
            ],
        ),
        html.Div(
            className="controls",
            children=[
                html.Div(
                    className="control",
                    children=[
                        html.Label("Date range"),
                        dcc.DatePickerRange(
                            id="date-range",
                            min_date_allowed=MIN_DATE,
                            max_date_allowed=MAX_DATE,
                            start_date=MIN_DATE,
                            end_date=MAX_DATE,
                            display_format="MMM YYYY",
                        ),
                    ],
                ),
                html.Div(
                    className="control",
                    children=[
                        html.Label("Avocado type"),
                        dcc.Checklist(
                            id="type-filter",
                            options=[{"label": f" {t}", "value": t} for t in ALL_TYPES],
                            value=ALL_TYPES,
                            inline=True,
                            className="checklist",
                        ),
                    ],
                ),
                html.Div(
                    className="control",
                    children=[
                        html.Label("Regions"),
                        dcc.Dropdown(
                            id="region-filter",
                            options=[{"label": r, "value": r} for r in ALL_REGIONS],
                            value=["TotalUS"],
                            multi=True,
                            placeholder="All regions",
                        ),
                    ],
                ),
                html.Div(
                    className="control",
                    children=[
                        html.Label("Region scope"),
                        dcc.RadioItems(
                            id="region-scope",
                            options=[
                                {"label": " All regions", "value": "all"},
                                {"label": " Metro areas only", "value": "metro"},
                                {"label": " Aggregates only", "value": "aggregate"},
                            ],
                            value="all",
                            className="checklist",
                        ),
                    ],
                ),
            ],
        ),
        html.Div(
            className="kpi-row",
            children=[
                kpi_card("kpi-avg-price", "Avg. price / avocado"),
                kpi_card("kpi-total-volume", "Total volume sold"),
                kpi_card("kpi-total-bags", "Total bags sold"),
                kpi_card("kpi-n-regions", "Regions in view"),
            ],
        ),
        html.Div(
            className="chart-grid",
            children=[
                html.Div(className="chart-card", children=dcc.Graph(id="price-trend")),
                html.Div(className="chart-card", children=dcc.Graph(id="volume-trend")),
                html.Div(className="chart-card", children=dcc.Graph(id="top-regions")),
                html.Div(className="chart-card", children=dcc.Graph(id="bag-mix")),
            ],
        ),
        html.Footer(
            "Data: Hass Avocado Board (via Kaggle) · Built with Dash & Plotly",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


def filter_data(start_date, end_date, types, scope, regions=None):
    dff = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
    if types:
        dff = dff[dff["type"].isin(types)]
    if scope == "metro":
        dff = dff[~dff["is_aggregate"]]
    elif scope == "aggregate":
        dff = dff[dff["is_aggregate"]]
    if regions:
        dff = dff[dff["region"].isin(regions)]
    return dff


@app.callback(
    Output("kpi-avg-price", "children"),
    Output("kpi-total-volume", "children"),
    Output("kpi-total-bags", "children"),
    Output("kpi-n-regions", "children"),
    Output("price-trend", "figure"),
    Output("volume-trend", "figure"),
    Output("top-regions", "figure"),
    Output("bag-mix", "figure"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("type-filter", "value"),
    Input("region-filter", "value"),
    Input("region-scope", "value"),
)
def update_dashboard(start_date, end_date, types, regions, scope):
    dff = filter_data(start_date, end_date, types, scope, regions=regions)

    if dff.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            template="plotly_white",
            annotations=[
                {
                    "text": "No data for this selection",
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {"size": 16},
                }
            ],
        )
        return "–", "–", "–", "0", empty_fig, empty_fig, empty_fig, empty_fig

    avg_price = f"${dff['average_price'].mean():.2f}"
    total_volume = f"{dff['total_volume'].sum() / 1e6:,.1f}M"
    total_bags = f"{dff['total_bags'].sum() / 1e6:,.1f}M"
    n_regions = f"{dff['region'].nunique()}"

    # Price trend: weekly average price by type
    price_trend_df = (
        dff.groupby(["date", "type"], as_index=False)["average_price"].mean()
    )
    fig_price = px.line(
        price_trend_df,
        x="date",
        y="average_price",
        color="type",
        color_discrete_map=TYPE_COLORS,
        labels={"date": "Date", "average_price": "Avg. price ($)", "type": "Type"},
        title="Average price over time",
    )
    fig_price.update_layout(template="plotly_white", legend_title_text="")

    # Volume trend: total volume by type (line, not stacked — conventional
    # volume dwarfs organic, so stacking would visually hide the organic
    # trend rather than reveal it).
    volume_trend_df = (
        dff.groupby(["date", "type"], as_index=False)["total_volume"].sum()
    )
    fig_volume = px.line(
        volume_trend_df,
        x="date",
        y="total_volume",
        color="type",
        color_discrete_map=TYPE_COLORS,
        labels={"date": "Date", "total_volume": "Volume sold", "type": "Type"},
        title="Sales volume over time",
    )
    fig_volume.update_layout(template="plotly_white", legend_title_text="")

    # Top regions by volume — ranked across all regions matching the
    # date/type/scope filters, independent of the region dropdown (ranking
    # a single already-selected region against itself wouldn't be useful).
    # Aggregates (e.g. TotalUS, California) are excluded so the ranking is
    # always metro-level, unless the user explicitly asked for aggregates.
    rank_base_df = filter_data(start_date, end_date, types, scope)
    region_rank_df = (
        rank_base_df if scope == "aggregate" else rank_base_df[~rank_base_df["is_aggregate"]]
    )
    top_regions_df = (
        region_rank_df.groupby("region", as_index=False)["total_volume"]
        .sum()
        .nlargest(10, "total_volume")
        .sort_values("total_volume")
    )
    fig_top_regions = px.bar(
        top_regions_df,
        x="total_volume",
        y="region",
        orientation="h",
        labels={"total_volume": "Total volume", "region": ""},
        title="Top 10 regions by volume",
    )
    fig_top_regions.update_traces(marker_color="#3E7C59")
    fig_top_regions.update_layout(template="plotly_white")

    # Bag size mix
    bag_totals = dff[["small_bags", "large_bags", "xlarge_bags"]].sum()
    fig_bag_mix = px.pie(
        names=["Small bags", "Large bags", "XL bags"],
        values=bag_totals.values,
        hole=0.5,
        title="Bag size mix",
    )
    fig_bag_mix.update_layout(template="plotly_white")

    return (
        avg_price,
        total_volume,
        total_bags,
        n_regions,
        fig_price,
        fig_volume,
        fig_top_regions,
        fig_bag_mix,
    )


if __name__ == "__main__":
    debug = os.environ.get("DASH_DEBUG", "true").lower() == "true"
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=debug, host="0.0.0.0", port=port)
