This is a work in progress.

Code Metrics
============

Code metrics is a simple Python module that leverage the libraries below to 
generate insight from a source control management (SCM) tool:

- pandas: for data munching.
- lizard: for code complexity calculation.
- cloc.pl (script): for line counts from [cloc](http://cloc.sourceforge.net/).
- and your SCM: for now, only Subversion is supported. Looking to add git.

It can generate reports based on Adam Tornhill awesome books.


Installation
============

```
pip install codemetrics
```


Recipes
=======

Derive components from path
---------------------------

```
df['component'] = df['path'].str.split('\\').str.get(-2)
```

Will add a component column equal to the parent folder of the path. If no
folder exists, it will show N/A.

For more advanced manipulation like extractions, see [Pandas documentation](https://pandas.pydata.org/pandas-docs/stable/text.html)


Aggregate hotspots by component
-------------------------------

```
hotspots_report = cm.HotSpotReport('.')
log, cloc = hotspots_report.get_log(), hotspots_report.get_cloc()
cloc['component'] = cloc['path'].str.split('\\').str.get(-2)
log['component'] = log['path'].str.split('\\').str.get(-2)
hspots = hotspots_report.generate(log,
                                  cloc.groupby('component').sum().reset_index(),
                                  by='component').dropna()
hspots.set_index(['component']).sort_values(by='score', ascending=False)
```

Will order hotspots at the component level in descending order based on the 
complexity and the number of changes (see score column).

