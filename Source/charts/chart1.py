import altair as alt

# Revenue by city
chart = (
    alt.Chart(df)
    .mark_bar()
    .encode(
        x=alt.X("City:N", sort="-y"),
        y=alt.Y("sum(Revenue):Q"),
        tooltip=["City:N", alt.Tooltip("sum(Revenue):Q", title="Total Revenue")],
    )
    .properties(title="Revenue by City")
)
