# Questions in disinformation

Below are instructions for getting started with this project and with Python. But quite often things don't quite work the same way on every system, so let me know if you get stuck!

## Project structure

I've reorganized the project to be a bit more modular. When you want to make a change, always consider _where_ to make this change:

- `analyze_tweets.py` takes a .csv file with raw tweets, computes various features and writes the result to a new .csv file (default name: `data/analyzed_tweets.csv`) and displays a histogram. The created .csv file will contain all the tweets, with the newly computed features as additional columns.
- `analyze_questions.py` takes the .csv file from the previous step (containing tweets with the additional features) and extracts questions from it, which it writes (together with some question-level features) to a new .csv file (default name: `data/analyzed_questions.csv`.
- `config.py` specifies paths to the data files you want to analyze, as well as the path to the .csv files that will be created by the different scripts, and some other 'purely bureaucratic' settings. In the other scripts, you may see `import config` (along with `import ling` and `import utils`, see below), which is how these scripts access the settings in the `config.py` file. Config is meant to be customized by you, as each person may be analyzing different datasets, stored in different places on your local drive.
- `ling.py` contains all the linguistically interesting bits, e.g., keywords, negations, a function to extract questions, a function to get the wh-word of a question, and so on. This file will be customized and expanded a lot as we will be implementing more and more linguistic features of interest.
- `utils.py` contains some leftover, generic utility functions, such as loading a tweet .csv file or matching a list of keywords, that you probably won't need to customize.

I'm not 100% happy yet with the division of labor (e.g., what if you want to analyze tweets _without_ creating a new .csv file?), but this should get us going for now.

## Cloning this git repository to create a new PyCharm project

1. Install PyCharm free community edition.  https://www.jetbrains.com/pycharm/
2. Starting PyCharm brings you to the welcome screen. (If you already had PyCharm running before, close all projects in PyCharm (e.g., File --> Close all projects) to return to the welcome screen.)
3. In the top-right corner of the welcome screen, click the button to import from 'VCS' (version control system) to create a new project from this Github repository's URL.
4. This creates a fresh project, so if already downloaded some data/code before, you need to move such files into the newly created folder (using your standard file explorer). Place .csv files containing tweets in the `data` folder.
5. Once the project is loaded, find the project settings somewhere (in windows and Linux I believe it is under `File > Settings` in the menu bar, also reachable via `ctrl-alt-s`; on Mac you can reach it at least via the cogwheel icon in the top right).
6. In `settings`, on the left you'll see `Project: disque > project interpreter`; go there.
7. There's a dropdown box there that may or may not contain anything. Click the cog-wheel next to it, then `add`.
8. Create a new `virtual environment`. All the default settings are fine, as long as the Python version is greater than 3.6.
9. (I think this will work automatically, but perhaps make sure the virtual environment you just created is now selected in the drop-down box as your project interpreter.)

## Updating the project

1. If someone updates the code in the github.com repository (the **remote**), you can go the menu `git` --> `pull` to download the changes from the **remote** and update your **local** PyCharm project.
2. If you yourself have made a change you really like, you can **commit** them (git --> commit, which will open panel on the left; select which files to commit) and then **push** the thusly staged commits to the github.com repository. Everyone else can then _pull_ them to their local projects.
3. What if you have local changes and try to pull from remote?
   - If you have any _uncommitted_ changes in your local project, PyCharm will warn you and the `pull` will be aborted. 
   - If you have _committed_ changes in your local project, pulling from remote will cause PyCharm to attempt to automatically **merge** the remote changes with the local changes (and the merged version will be stored in a new 'commit', that you can, in turn, push back to the **remote** so everyone can _pull_ the merged version); if for some reason automatic merge is not possible, it will ask you to manually indicate which changes to adopt. This can be a bit tricky though.
4. In general, the remote repository should be kept in 'good' shape; only commit and push something if at least the code runs. So for any more 'temporary' changes you want to share with each other, consider also sharing them via chat instead.