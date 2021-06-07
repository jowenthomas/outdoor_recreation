import json
import requests
import pandas as pd
from bokeh.models import ColumnDataSource, PreText

from flask import Flask
from jinja2 import Template

from bokeh.embed import json_item
from bokeh.plotting import figure
from bokeh.resources import CDN
from bokeh.sampledata.iris import flowers

'''Manual version of api request...need to fix'''
key = 'J65G2QPKESHV5PY6'
ticker = 'AAPL'
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={}&apikey={}&outputsize=compact'.format(ticker, key)

# get data from api
apiresponse = requests.get(url)

#easier, i think, to clean up the dictionary with python before passing into pandas
dictio = apiresponse.json()
dictio.pop('Meta Data')
close_dict = {key: value['4. close'] for key, value in dictio['Time Series (Daily)'].items()}

# setup and clean df
df = pd.DataFrame(close_dict.items(), columns=['date', 'close'])
df['date']= pd.to_datetime(df['date'])
#limit to 30
df = df.iloc[0:30]

# setup figure for bokeh
source = ColumnDataSource(df)

app = Flask(__name__)

page = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
  {{ resources }}
</head>
<body>
    
    <div id="myplot"></div>
    <div id="mystats"></div>
  <script>
  fetch('/plot')
    .then(function(response) { return response.json(); })
    .then(function(item) { return Bokeh.embed.embed_item(item); })
  </script>
  <script>
  fetch('/stats')
    .then(function(response) { return response.json(); })
    .then(function(item) { return Bokeh.embed.embed_item(item); })
  </script>
</body>
""")

# ===for input form===
@app.route('/')
def root():
    return page.render(resources=CDN.render())


# ===for plot===
def make_plot():
  p = figure(title="Closing Price: Previous 30 Days", x_axis_label='Date', x_axis_type='datetime', y_axis_label='CLosing Price (USD)')
  p.line(x='date', y='close', legend_label=ticker, source=source, line_width=2)
  return p

@app.route('/plot')
def plot():
    p = make_plot()
    return json.dumps(json_item(p, "myplot"))

# ===for stats summary===
stats_text = str(pd.to_numeric(df['close']).describe())
stats_text = stats_text[:-29]

def make_summary():
    pre = PreText(text=stats_text, width=500, height=100)
    return pre

@app.route('/stats')
def summary():
    pre = make_summary()
    return json.dumps(json_item(pre, "mystats"))


if __name__ == '__main__':
    app.run()