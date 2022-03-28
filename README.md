# Questions in disinformation

Below are instructions for getting started with this project and with Python. But quite often things don't quite work the same way on every system, so let me know if you get stuck!

## Cloning this git repository

1. Above, click on the green button `code` and then `download zip`.
2. Unzip the downloaded file in some place on your home drive, e.g., inside a folder you call `projects`. This will create a `disque` folder inside the `projects` folder.

## Opening the `disque` folder as a project in PyCharm

1. Install PyCharm free community edition.  https://www.jetbrains.com/pycharm/
2. Once inside, click 'Open' and select the `disque` folder you downloaded and unzipped before.
3. Once the project is loaded, find the project settings somewhere (in windows and Linux I believe it is under `File > Settings` in the menu bar, also reachable via `ctrl-alt-s`).
4. In `settings`, on the left you'll see `Project: disque > project interpreter`; go there.
5. There's a dropdown box there that may or may not contain anything. Click the cog-wheel next to it, then `add`.
6. Create a new `virtual environment`. All the default settings are fine, as long as the Python version is greater than 3.6.
7. (I think this will work automatically, but perhaps make sure the virtual environment you just created is now selected in the drop-down box as your project interpreter.)

## Data

Place .csv files containing tweets in the `data` folder.

## An exploration script

1. From the project panel on the left, open the file `squib.py`. It will now appear in the 'editor'. There will likely be red squiggles underneath `import pandas` and `import seaborn`. Hover over them and click `install`. This can take a brief while.
2. Hitting `ctrl-shift-F10` should run the `squib.py` file, though on some systems the hotkey may be different. If you cannot find the hotkey, in the editor scroll down to the line that says `if __name__ == '__main__':` as next to it there should be a green arrow you can click.
3. (After you've run it once the first time, you can also run it with `shift-F10` or with the green arrow button in the top toolbar.)
4. Running the `squib.py` file should make a histogram (plot) appear, as well as some printed output at the bottom. If not, something's wrong.
5. Have a look at the code and start messing around. (You always need to close the plot manually before the code continues running. You can also 'comment out' the line `plt.show()` (by putting `#` in front of it) so the plot doesn't appear, in case you're tired of it.)