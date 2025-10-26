from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd, numpy as np, json, os, tempfile, matplotlib.pyplot as plt, imageio

app = Flask(__name__)

def generate_sample_data():
    start = pd.Timestamp("2024-06-01")
    months = pd.date_range(start, periods=19, freq='MS')
    business_functions = ["Finance","HR","Sales","Marketing","Customer Ops","Engineering","Legal","Analytics","Procurement"]
    rng = np.random.default_rng(42)
    records=[]
    for bf in business_functions:
        base_ws=rng.integers(3,30); base_tb=float(rng.uniform(0.2,8.0))
        for i,m in enumerate(months):
            growth_ws=int(base_ws+np.clip(rng.normal(i*0.6,1.5),0,None))
            growth_tb=round(base_tb+max(0,rng.normal(i*0.8,0.8)),3)
            records.append({"month":m,"business_function":bf,"workspace_count":growth_ws,"data_volume_tb":growth_tb})
    df=pd.DataFrame(records).sort_values(["month","business_function"])
    df["cumulative_tb"]=df.groupby("business_function")["data_volume_tb"].cumsum()
    df["cumulative_workspaces"]=df.groupby("business_function")["workspace_count"].cumsum()
    return df

DATA=generate_sample_data()

@app.route("/")
def index():
    bfs=sorted(DATA["business_function"].unique())
    months=sorted(DATA["month"].dt.strftime("%Y-%m").unique())
    return render_template("index.html",business_functions=bfs,months=months)

@app.route("/data")
def data():
    bf=request.args.get("business_function")
    m=request.args.get("month")
    df=DATA.copy()
    if bf and bf!="__all": df=df[df["business_function"]==bf]
    if m and m!="__all": df=df[df["month"].dt.strftime("%Y-%m")==m]
    df["month_str"]=df["month"].dt.strftime("%Y-%m")
    import plotly.express as px
    fig=px.bar(df,x="workspace_count",y="business_function",color="business_function",orientation="h",
               animation_frame="month_str",range_x=[0,max(df["workspace_count"].max()*1.2,10)],
               labels={"workspace_count":"Workspace Count","business_function":"Business Function"})
    fig.update_layout(height=600,showlegend=False,title="Workspace Migration Count by Business Function (Monthly)")
    return jsonify(plotly_fig=json.loads(fig.to_json()))

@app.route("/upload",methods=["POST"])
def upload():
    f=request.files.get("file")
    if not f:return jsonify({"status":"error"}),400
    global DATA
    df=pd.read_csv(f)
    df["month"]=pd.to_datetime(df["month"])
    DATA=df
    return jsonify({"status":"ok"})

@app.route("/download_csv")
def download_csv():
    tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".csv")
    DATA.to_csv(tmp.name,index=False)
    return send_file(tmp.name,as_attachment=True,download_name="migration_data.csv")

@app.route("/generate_video",methods=["POST"])
def generate_video():
    df=DATA.copy();df["month_str"]=df["month"].dt.strftime("%Y-%m")
    months=sorted(df["month_str"].unique())
    tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".mp4")
    frames=[]
    for m in months:
        d=df[df["month_str"]==m].sort_values("workspace_count",ascending=True)
        fig,ax=plt.subplots(figsize=(8,5))
        ax.barh(d["business_function"],d["workspace_count"],color="skyblue")
        ax.set_title(f"Workspace Migration - {m}")
        ax.set_xlabel("Workspace Count")
        for i,(val,name) in enumerate(zip(d["workspace_count"],d["business_function"])):
            ax.text(val+1,i,name,va='center')
        plt.tight_layout()
        tmpimg=tempfile.NamedTemporaryFile(delete=False,suffix=".png")
        plt.savefig(tmpimg.name);plt.close(fig)
        frames.append(imageio.imread(tmpimg.name))
        os.remove(tmpimg.name)
    imageio.mimsave(tmp.name,frames,fps=2)
    return jsonify({"url":f"/video/{os.path.basename(tmp.name)}"})

@app.route("/video/<fname>")
def get_video(fname):
    return send_file(os.path.join(tempfile.gettempdir(),fname),as_attachment=True,download_name="migration_animation.mp4")

if __name__=="__main__":
    app.run(debug=True)
