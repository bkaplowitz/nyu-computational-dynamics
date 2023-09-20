# make sure the following libraries are installed
# !pip install --upgrade pandas-datareader
# !pip install --upgrade yfinance

# import necessary libraries
import pandas as pd
import pandas_datareader as pdr
import numpy as np
from scipy import stats
from scipy import optimize
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.ticker as ticker
from io import BytesIO
import requests
import datetime

# ------------------------------------------------------------------------------
# calculation date as a fraction of the year, from a datetime vector
def year_frac(ts):
    yf = np.empty(ts.size)
    for i in range(ts.size):
        days = 365 + ts[i].is_leap_year*1
        yf[i] = ts[i].year + ts[i].dayofyear/days + ts[i].hour/24/days + ts[i].minute/60/24/days + ts[i].second/60/60/24/days
    return yf

# ------------------------------------------------------------------------------
# read data from FRED
def myLoadDataFRED(series,transform='none',start = datetime.datetime(1800,1,1),end = datetime.datetime(2050,1,1)):
    # work out start and end 
    data = pdr.data.DataReader(series,'fred',start,end)
    d = {'orig': data, 'transform': transform, 'year': year_frac(ts=data.index)}
    d['freq'] = int(round(1/(d['year'][1]-d['year'][0]),0))
    T = len(d['year'])
    for i in series:
        d[i] = data[i].to_numpy()
        if transform=='pct_change_year_ago':
            d[i][d['freq'] : T] = (
                (d[i][d['freq'] : T] - d[i][: T - d['freq']])
                / d[i][: T - d['freq']]
                * 100
            )
            d[i][:d['freq']] = float('nan')

    return d

# ==============================================================================
# a slight modification of the OECDReader that allows the specification of
# dataset/series, instead of just a complete dataset
# example: NAAG/.B9S13S for URL https://stats.oecd.org/SDMX-JSON/data/NAAG/.B9S13S/all
#          SNA_TABLE1/.B1_GA. for URL https://stats.oecd.org/SDMX-JSON/data/SNA_TABLE1/.B1_GA./all

from pandas_datareader.base import _BaseReader
from pandas_datareader.compat import string_types
from pandas_datareader.io import read_jsdmx

class OECDReaderSeries(_BaseReader):
    """Get data for the given name from OECD."""

    _format = "json"

    @property
    def url(self):
        """API URL"""
        url = "https://stats.oecd.org/SDMX-JSON/data"

        if not isinstance(self.symbols, string_types):
            raise ValueError("data name must be string")

        # API: https://data.oecd.org/api/sdmx-json-documentation/
        return "{0}/{1}/all?".format(url, self.symbols)

    def _read_lines(self, out):
        """read one data from specified URL"""
        df = read_jsdmx(out)
        try:
            idx_name = df.index.name  # hack for pandas 0.16.2
            df.index = pd.to_datetime(df.index, errors="ignore")
            for col in df:
                df[col] = pd.to_numeric(df[col], errors="ignore")
            df = df.sort_index()
            df = df.truncate(self.start, self.end)
            df.index.name = idx_name
        except ValueError:
            pass
        return df