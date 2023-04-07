## Running the indexer locally

First, install requirements in a venv :

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Then, create a `config.toml` based on the template provided. You'll need to update the mongoDB connection string.

Finally, run the indexer locally with:

```bash
python3 indexer
```
