# =============================================================================
# Ski Resort Currency Dashboard Framework
# Segmented views for volume markets vs luxury feeder markets
# =============================================================================

library(tidyverse)
library(lubridate)
library(scales)

# -----------------------------------------------------------------------------
# 1. CURRENCY CONFIGURATION
# -----------------------------------------------------------------------------

# Volume markets (drive visitation counts)
volume_currencies <- tribble(
  ~currency, ~name,                  ~segment,     ~primary_destination,
  "CAD",     "Canadian Dollar",      "volume",     "both",

  "MXN",     "Mexican Peso",         "volume",     "us",
  "EUR",     "Euro",                 "volume",     "both",
  "GBP",     "British Pound",        "volume",     "both",
  "AUD",     "Australian Dollar",    "volume",     "whistler"
)

# Luxury feeder markets (drive ancillary spend, length of stay)
luxury_currencies <- tribble(
  ~currency, ~name,                  ~segment,     ~primary_destination,
  "HKD",     "Hong Kong Dollar",     "luxury",     "both",
  "SGD",     "Singapore Dollar",     "luxury",     "both",
  "AED",     "UAE Dirham",           "luxury",     "aspen",
  "BRL",     "Brazilian Real",       "luxury",     "aspen",
  "RUB",     "Russian Ruble",        "luxury",     "both",
  "INR",     "Indian Rupee",         "luxury",     "both",
  "CNY",     "Chinese Yuan",         "luxury",     "whistler",
  "JPY",     "Japanese Yen",         "luxury",     "whistler"
)

# Combine for full config
currency_config <- bind_rows(volume_currencies, luxury_currencies)

# -----------------------------------------------------------------------------
# 2. THRESHOLD CONFIGURATION
# -----------------------------------------------------------------------------

# Volume market thresholds (absolute levels that trigger behavioral shifts)
volume_thresholds <- tribble(
  ~currency, ~favorable_us, ~unfavorable_us, ~favorable_ca, ~unfavorable_ca, ~notes,
  "CAD",     1.40,          1.25,            1.25,          1.40,            "Key cross-border threshold",
  "MXN",     16.0,          20.0,            NA,            NA,              "Mexican travel to US",
  "EUR",     0.95,          0.85,            NA,            NA,              "European travel sensitivity",
  "GBP",     0.82,          0.72,            NA,            NA,              "UK travel sensitivity",
  "AUD",     1.60,          1.45,            NA,            NA,              "Australian travel to Whistler"
)

# Luxury market thresholds (deviation from rolling average)
luxury_thresholds <- tribble(
  ~metric,                ~favorable, ~unfavorable, ~notes,
  "pct_vs_3yr_avg",       -10,        10,           "% deviation from 3-year rolling average",
  "pct_vs_prior_visit",   -15,        15,           "% change since typical booking window (6mo)"
)

# -----------------------------------------------------------------------------
# 3. DATA TRANSFORMATION FUNCTIONS
# -----------------------------------------------------------------------------

#' Reorient exchange rates for destination perspective
#' @param rate Current exchange rate (foreign currency per USD)
#' @param base_amount Amount of foreign currency (default 100)
#' @return USD purchasing power of foreign currency
calc_visitor_purchasing_power <- function(rate, base_amount = 100) {
  base_amount / rate
}

#' Calculate CAD purchasing power for Canadian resort perspective
#' @param usd_cad Current USD/CAD rate
#' @param foreign_usd Current foreign currency per USD rate
#' @return CAD purchasing power of foreign currency (via USD cross)
calc_cad_purchasing_power <- function(usd_cad, foreign_usd) {
  # Foreign visitor perspective: how much CAD does 100 units of their currency buy?
  (100 / foreign_usd) * usd_cad
}

#' Calculate deviation from rolling average
#' @param current Current rate
#' @param historical Vector of historical rates
#' @param window Rolling window in days (default 3 years)
#' @return Percent deviation from rolling average
calc_deviation_from_avg <- function(current, historical, window = 1095) {
  avg <- mean(tail(historical, window), na.rm = TRUE)
  ((current - avg) / avg) * 100
}

#' Assign threshold status
#' @param value Current value
#' @param favorable Favorable threshold
#' @param unfavorable Unfavorable threshold
#' @param lower_is_better If TRUE, lower values are favorable (default FALSE)
#' @return Status: "favorable", "unfavorable", or "neutral"
assign_threshold_status <- function(value, favorable, unfavorable, lower_is_better = FALSE) {
  if (is.na(favorable) | is.na(unfavorable)) return("neutral")
  
  if (lower_is_better) {
    case_when(
      value <= favorable ~ "favorable",
      value >= unfavorable ~ "unfavorable",
      TRUE ~ "neutral"
    )
  } else {
    case_when(
      value >= favorable ~ "favorable",
      value <= unfavorable ~ "unfavorable",
      TRUE ~ "neutral"
    )
  }
}

# -----------------------------------------------------------------------------
# 4. DASHBOARD VIEW GENERATORS
# -----------------------------------------------------------------------------

#' Generate US Resort Operator View
#' Perspective: "How attractive is the US as a destination for international skiers?"
generate_us_resort_view <- function(rates_df) {
  
  rates_df |>
    filter(currency %in% c("CAD", "MXN", "EUR", "GBP", "BRL", "AUD")) |>
    mutate(
      # How many USD does 100 units of visitor currency buy?
      visitor_usd_power = calc_visitor_purchasing_power(rate_per_usd),
      
      # Reframe: higher = more attractive for visitors
      visitor_friendly_label = paste0(
        "$", round(visitor_usd_power, 2), " USD per 100 ", currency
      ),
      
      # YoY context
      yoy_direction = case_when(
        yoy_change < -5 ~ "improving",      # Their currency strengthening vs USD
        yoy_change > 5  ~ "deteriorating",  # Their currency weakening vs USD
        TRUE ~ "stable"
      )
    ) |>
    select(currency, name, visitor_usd_power, visitor_friendly_label, 
           yoy_change, yoy_direction, segment)
}

#' Generate Canadian Resort Operator View
#' Perspective: "How attractive is Canada for US visitors, and how competitive vs alternatives?"
generate_ca_resort_view <- function(rates_df) {
  
  usd_cad <- rates_df |> filter(currency == "CAD") |> pull(rate_per_usd)
  
  rates_df |>
    mutate(
      # For US visitors: How many CAD does $100 USD buy?
      us_visitor_cad_power = if_else(
        currency == "CAD",
        100 * usd_cad,  # $100 USD buys this many CAD
        NA_real_
      ),
      
      # For international visitors: Cross-rate via USD
      intl_visitor_cad_power = if_else(
        currency != "CAD",
        calc_cad_purchasing_power(usd_cad, rate_per_usd),
        NA_real_
      ),
      
      # Competitive positioning vs other destinations
      # Lower CAD = more competitive vs Alps (EUR), Japan (JPY), etc.
      competitive_context = case_when(
        currency == "EUR" ~ "vs Alps",
        currency == "JPY" ~ "vs Niseko",
        currency == "CHF" ~ "vs Swiss resorts",
        currency == "AUD" ~ "vs Australian domestic",
        TRUE ~ NA_character_
      )
    )
}

#' Generate Luxury Segment View
#' Perspective: "Deviation from norms that drive advisor recommendations"
generate_luxury_view <- function(rates_df, historical_rates_df) {
  
  rates_df |>
    filter(currency %in% luxury_currencies$currency) |>
    rowwise() |>
    mutate(
      # Get historical series for this currency
      hist_series = list(
        historical_rates_df |> 
          filter(currency == .data$currency) |> 
          pull(rate_per_usd)
      ),
      
      # Calculate deviation from 3-year average
      pct_vs_3yr_avg = calc_deviation_from_avg(rate_per_usd, hist_series[[1]]),
      
      # Luxury-specific status
      luxury_status = case_when(
        pct_vs_3yr_avg <= -10 ~ "USD cheap (favorable)",
        pct_vs_3yr_avg >= 10  ~ "USD expensive (unfavorable)",
        TRUE ~ "Within normal range"
      ),
      
      # Advisor talking point
      advisor_note = case_when(
        pct_vs_3yr_avg <= -10 ~ paste0(
          "USD is ", abs(round(pct_vs_3yr_avg, 1)), 
          "% cheaper than 3-year average"
        ),
        pct_vs_3yr_avg >= 10 ~ paste0(
          "USD is ", round(pct_vs_3yr_avg, 1), 
          "% more expensive than 3-year average"
        ),
        TRUE ~ "Exchange rate within typical range"
      )
    ) |>
    ungroup() |>
    select(currency, name, rate_per_usd, pct_vs_3yr_avg, luxury_status, advisor_note)
}

# -----------------------------------------------------------------------------
# 5. DOMESTIC RETENTION VIEW (Canadian operators)
# -----------------------------------------------------------------------------

#' Generate Domestic Retention View for Canadian Operators
#' Perspective: "How likely are Canadians to stay home vs travel to US?"
generate_domestic_retention_view <- function(rates_df) {
  
  usd_cad <- rates_df |> filter(currency == "CAD") |> pull(rate_per_usd)
  
  tibble(
    metric = c(
      "CAD per USD",
      "Cost of $100 USD trip expense in CAD",
      "Retention signal"
    ),
    value = c(
      round(usd_cad, 4),
      round(100 * usd_cad, 2),
      NA_real_
    ),
    status = c(
      NA_character_,
      NA_character_,
      case_when(
        usd_cad >= 1.40 ~ "Strong retention (USD expensive for Canadians)",
        usd_cad <= 1.25 ~ "Weak retention (USD cheap for Canadians)",
        TRUE ~ "Neutral"
      )
    ),
    context = c(
      paste0("YoY: ", rates_df |> filter(currency == "CAD") |> pull(yoy_change), "%"),
      "What a Canadian pays for US-priced goods/services",
      "Above 1.40: Canadians more likely to ski domestically"
    )
  )
}

# -----------------------------------------------------------------------------
# 6. SAMPLE DATA STRUCTURE (replace with your actual data feed)
# -----------------------------------------------------------------------------

# Example current rates (you'd replace with API feed)
sample_current_rates <- tribble(
  ~currency, ~name,                ~rate_per_usd, ~yoy_change, ~change_30d,
  "CAD",     "Canadian Dollar",    1.3738,        -4.3,        -2.2,
  "MXN",     "Mexican Peso",       17.88,         -11.8,       -2.5,
  "EUR",     "Euro",               0.8519,        -11.4,       -1.7,
  "GBP",     "British Pound",      0.7418,        -7.1,        -3.0,
  "JPY",     "Japanese Yen",       156.72,        -0.5,        0.1,
  "CNY",     "Chinese Yuan",       6.9877,        -4.6,        -1.7,
  "INR",     "Indian Rupee",       90.19,         5.2,         1.8,
  "AUD",     "Australian Dollar",  1.4961,        -6.5,        -3.2,
  "RUB",     "Russian Ruble",      80.21,         -12.1,       NA,
  "HKD",     "Hong Kong Dollar",   7.78,          -0.2,        -0.1,
  "SGD",     "Singapore Dollar",   1.32,          -3.8,        -1.5,
  "AED",     "UAE Dirham",         3.67,          0.0,         0.0,
  "BRL",     "Brazilian Real",     5.05,          8.2,         2.1
) |>
  left_join(currency_config, by = c("currency", "name"))

# -----------------------------------------------------------------------------
# 7. GENERATE ALL VIEWS
# -----------------------------------------------------------------------------

# For demonstration (replace sample data with your actuals)
us_resort_view <- generate_us_resort_view(sample_current_rates)
ca_resort_view <- generate_ca_resort_view(sample_current_rates)
domestic_retention_view <- generate_domestic_retention_view(sample_current_rates)

# Print sample outputs
cat("=== US RESORT OPERATOR VIEW ===\n")
print(us_resort_view)

cat("\n=== CANADIAN DOMESTIC RETENTION VIEW ===\n")
print(domestic_retention_view)

# -----------------------------------------------------------------------------
# 8. VISUALIZATION HELPERS
# -----------------------------------------------------------------------------

#' Color scale for threshold status
threshold_colors <- c(
  "favorable" = "#2E7D32",     # Green
  "neutral" = "#757575",       # Gray
  "unfavorable" = "#C62828"    # Red
)

#' Create sparkline-ready trend data
create_trend_summary <- function(historical_df, currency_code, days = 90) {
  historical_df |>
    filter(currency == currency_code) |>
    arrange(desc(date)) |>
    slice_head(n = days) |>
    summarise(
      trend_direction = case_when(
        last(rate_per_usd) > first(rate_per_usd) ~ "strengthening",
        last(rate_per_usd) < first(rate_per_usd) ~ "weakening",
        TRUE ~ "flat"
      ),
      pct_change = ((first(rate_per_usd) - last(rate_per_usd)) / last(rate_per_usd)) * 100,
      volatility = sd(rate_per_usd) / mean(rate_per_usd) * 100
    )
}

# -----------------------------------------------------------------------------
# 9. COMPETITIVE DESTINATION COMPARISON (for Whistler)
# -----------------------------------------------------------------------------

#' Compare CAD competitiveness vs alternative luxury ski destinations
generate_competitive_comparison <- function(rates_df) {
  
  usd_cad <- rates_df |> filter(currency == "CAD") |> pull(rate_per_usd)
  usd_eur <- rates_df |> filter(currency == "EUR") |> pull(rate_per_usd)
  usd_chf <- rates_df |> filter(currency == "CHF") |> pull(rate_per_usd)
  usd_jpy <- rates_df |> filter(currency == "JPY") |> pull(rate_per_usd)
  
  # Cross rates from perspective of USD-based traveler
  tibble(
    destination = c("Whistler (CAD)", "Alps - France/Austria (EUR)", 
                    "Alps - Switzerland (CHF)", "Niseko (JPY)"),
    currency = c("CAD", "EUR", "CHF", "JPY"),
    rate_per_usd = c(usd_cad, usd_eur, usd_chf, usd_jpy),
    usd_100_buys = c(
      100 * usd_cad,
      100 / usd_eur,
      100 / usd_chf,
      100 * usd_jpy
    ),
    relative_value_note = c(
      paste0("$100 USD = $", round(100 * usd_cad, 0), " CAD"),
      paste0("$100 USD = €", round(100 * usd_eur, 0)),
      paste0("$100 USD = CHF ", round(100 * usd_chf, 0)),
      paste0("$100 USD = ¥", format(round(100 * usd_jpy, 0), big.mark = ","))
    )
  )
}

cat("\n=== COMPETITIVE DESTINATION COMPARISON ===\n")
# Note: CHF not in sample data, would need to add
# print(generate_competitive_comparison(sample_current_rates))
