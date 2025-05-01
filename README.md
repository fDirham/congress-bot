## Overview

A project to grab congress stock data from publically available sites

## Setup

1. Create python venv in .venv
2. Add this to the bottom of activate script:

```
export PYTHONPATH="<path to project folder>"
```

3. `pip install -r requirements.txt`
4. `npm install`

## House data scraper

`node scrape_house_data.js --year 2024`

Use this to scrape everything:

```
node scrape_house_data.js --year 2024 && node scrape_house_data.js --year 2023 && node scrape_house_data.js --year 2022 && node scrape_house_data.js --year 2021 && node scrape_house_data.js --year 2020 && node scrape_house_data.js --year 2019 && node scrape_house_data.js --year 2018 && node scrape_house_data.js --year 2017 && node scrape_house_data.js --year 2016 && node scrape_house_data.js --year 2015 && node scrape_house_data.js --year 2014 && node scrape_house_data.js --year 2013 && node scrape_house_data.js --year 2012
```

## Senate data scraper

Use this to scrape everything:

```
node scrape_senate_data.js --year 2024 && node scrape_senate_data.js --year 2023 && node scrape_senate_data.js --year 2022 && node scrape_senate_data.js --year 2021 && node scrape_senate_data.js --year 2020 && node scrape_senate_data.js --year 2019 && node scrape_senate_data.js --year 2018 && node scrape_senate_data.js --year 2017 && node scrape_senate_data.js --year 2016 && node scrape_senate_data.js --year 2015 && node scrape_senate_data.js --year 2014 && node scrape_senate_data.js --year 2013 && node scrape_senate_data.js --year 2012
```
