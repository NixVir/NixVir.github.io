library(tidyquant)
library(fredr)
library(jsonlite)
library(httr)
library(dplyr)

# Function to fetch BLS data
fetch_bls_data <- function(series_ids) {
  api_key <- Sys.getenv("BLS_API_KEY")
  
  url <- "https://api.bls.gov/publicAPI/v2/timeseries/data/"
  
  payload <- list(
    seriesid = series_ids,
    startyear = as.character(format(Sys.Date() - 365, "%Y")),
    endyear = as.character(format(Sys.Date(), "%Y")),
    registrationkey = api_key
  )
  
  response <- POST(url, 
                   body = toJSON(payload, auto_unbox = TRUE),
                   content_type_json())
  
  content(response, "parsed")
}

fetch_dashboard_data <- function() {
  # Set API keys
  fredr_set_key(Sys.getenv("FRED_API_KEY"))
  
  cat("Fetching FRED data...\n")
  # Get consumer confidence
  consumer_conf <- fredr(
    series_id = "UMCSENT",
    observation_start = Sys.Date() - 365
  )
  
  cat("Fetching market data...\n")
  # Get market data
  market_data <- tq_get(
    c("SPY", "^VIX", "^DJI", "^GSPC"),
    from = Sys.Date() - 30
  ) %>%
    group_by(symbol) %>%
    slice_tail(n = 1) %>%
    select(symbol, date, close, volume)
  
  # Get Fed data - FIXED to get latest
  fed_rates <- fredr(series_id = "DFF", 
                     observation_start = Sys.Date() - 90,
                     observation_end = Sys.Date())
  fed_rates <- tail(fed_rates, 1)
  
  unemployment <- fredr(series_id = "UNRATE", 
                        observation_start = Sys.Date() - 90,
                        observation_end = Sys.Date())
  unemployment <- tail(unemployment, 1)
  
  cat("Fetching BLS data...\n")
  # Get BLS data
  bls_series <- c("CUSR0000SA0", "CES0000000001", "CES0500000003")
  bls_data <- fetch_bls_data(bls_series)
  
  # Parse BLS results
  cpi_data <- NULL
  employment_data <- NULL
  wage_data <- NULL
  
  if(bls_data$status == "REQUEST_SUCCEEDED") {
    for(series in bls_data$Results$series) {
      latest <- series$data[[1]]
      if(series$seriesID == "CUSR0000SA0") {
        cpi_data <- list(value = as.numeric(latest$value), 
                        period = paste(latest$year, latest$periodName))
      } else if(series$seriesID == "CES0000000001") {
        employment_data <- list(value = as.numeric(latest$value), 
                               period = paste(latest$year, latest$periodName))
      } else if(series$seriesID == "CES0500000003") {
        wage_data <- list(value = as.numeric(latest$value), 
                         period = paste(latest$year, latest$periodName))
      }
    }
  }
  
  # Create dashboard JSON
  dashboard <- list(
    updated = Sys.time(),
    consumer_confidence = tail(consumer_conf, 12),
    markets = market_data,
    fed_funds_rate = fed_rates,
    unemployment = unemployment,
    cpi = cpi_data,
    employment = employment_data,
    wages = wage_data
  )
  
  # Save to static folder
  dir.create("static/data", showWarnings = FALSE)
  write_json(dashboard, "static/data/dashboard.json", pretty = TRUE)
  
  cat("Dashboard data updated:", format(Sys.time()), "\n")
}

# Run it
fetch_dashboard_data()

