# TICK-PILOT BACKEND:

**Latest Releases**: `0.0.1`

```
version 0.0.1: Multiple Stocks Handling
- branch name (-b): multiple_stocks_server#v0.0.1
```

**Previous Releases.**:

```
version 0.0.0: Limited to single stock handling and no server interface.
- branch name (-b): single_stocks_only#v0.0.0
```

## <ins>Setup Guide</ins>:

### Daily Environment Updates [ACCESS_TOKEN Changes]:

1. **Edit `.env` with new ACCESS_TOKEN, then restart with**:

```
docker-compose up
```

---

### Initial Setup & Run [via Docker]:

_[**NOTE**: Initial Setup may take some time... (for first time only)]_

1. **Install Docker Desktop**:

- Download & install it from [here🔗](https://www.docker.com/get-started/) based on your operating system.
- Make Sure Docker Desktop in running/open, before you start testing...

2. **Clone the Repository and move inside Directory...[use git bash]**:

```
git clone https://github.com/ghelanikirtan/TickPilot
cd TickPilot/BACKEND
```

3. **Set Up Environment Variables**:

- Create a `.env` file in the folder containing ACCESS_TOKEN=your_token (as per the .env.example file reference).

4. **Start the App**:

```
docker-compose up
```

- The app will be available at [http://localhost:8000](http://localhost:8000)

---

### Updating the APP [For changes in the code]:

1. **Pull the latest Code from github**:

`git pull`

2. **Restart the APP**:

```
docker-compose down
docker-compoes up
```

**OR**

- Open file⚙️: `update-and-run.bat` [Only for Windows]

---

### Troubleshooting:

- Check the terminal output where `docker-compoes up` runs for error messages.

- If dependencies change (e.g., new packages in `requirements.txt`), use:

```
docker-compose up --build
```

---

### Setup & Run (OLD setup - deprecated | but works) ❌:

1. **Clone This Repository & move inside BACKEND directory:**

```
git clone https://github.com/ghelanikirtan/TickPilot
cd TickPilot/BACKEND
```

2. **Create Virtual Environment using conda distribution:**

```
conda create -p venv python==3.10.16 -y
```

3. **Activate the Environment:**

```
conda activate venv/
```

- **Install requirements:**

```
pip install -r requirements.txt
```

- **Create `.env` file and add your `ACCESS_TOKEN` generated from upstox.**

`ACCESS_TOKEN=paste-your-access-token`

- **Run the `main.py` file & sleep brother:**

```
python main.py
```

## INFO:

### Implemented Features:

- In between websocket subsrcibing (changing stocks, adding stocks parallely and start a new process tree) ~ enables multiple stocks handling...
- Enabled temporary server endpoints with user inputs [normal REST API].
- Basic Jinja based frontend (form for user input collection) developed.
- Dockerized an application [Can run in any system].

### Todo:

- Implement ISIN to STOCK based indexing pipeline to enable keyword searching.
- Design React Based Frontend and Integrate with the server.
- And Periodically Algorithamic Logic Improvements.
- Implement Short Trading Strategy. [v0.0.2]

---

### APP Building Guide [Final one cloud ready]:

1. **Clone the Repository**:

```
git clone -b <branch> https://github.com/ghelanikirtan/TickPilot
cd TickPilot/BACKEND
```

2. **Build a docker image...**:

```
docker build -t tick-pilot-app
```

3. **Run the build...**:

```
docker run --env-file .env -p 8000:8000 tick-pilot-app
```

4. **Open Browser & [localhost:8000](http://localhost:8000)**

5. **Begin deployment in cloud...**
