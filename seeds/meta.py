"""Tiny Meta API helper: loads key from staged .env (never printed), caches every response on disk."""
import os, json, hashlib, pathlib, urllib.request, time
ROOT = pathlib.Path(__file__).parent
for p in [pathlib.Path("/mnt/user-data/uploads/Meta_Hackathon/.env"), ROOT/".env"]:
    if p.exists():
        for l in p.read_text().splitlines():
            l=l.strip()
            if l and not l.startswith("#") and "=" in l:
                k,v=l.split("=",1); v=v.strip().strip('"').strip("'")
                if not v.startswith("REPLACE"): os.environ.setdefault(k.strip(), v)
KEY=os.environ["MODEL_API_KEY"]; BASE="https://api.meta.ai/v1"
CACHE=ROOT/"cache"; CACHE.mkdir(exist_ok=True)
USAGE=ROOT/"results"/"usage.jsonl"
def _cached(tag, payload_bytes, fn):
    h=hashlib.sha256(tag.encode()+payload_bytes).hexdigest()[:24]; f=CACHE/f"{h}.json"
    if f.exists(): return json.loads(f.read_text())
    t=time.time(); out=fn(); out["_latency_s"]=round(time.time()-t,2)
    if "body" not in out: f.write_text(json.dumps(out))
    
    with open(USAGE,"a") as u: u.write(json.dumps({"tag":tag,"usage":out.get("usage"),"lat":out["_latency_s"]})+"\n")
    return out
def responses(body, tag="resp"):
    data=json.dumps(body).encode()
    def call():
        r=urllib.request.Request(BASE+"/responses",data=data,headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json"})
        try: return json.load(urllib.request.urlopen(r,timeout=300))
        except urllib.error.HTTPError as e: return {"error":e.code,"body":e.read().decode()[:2000]}
    return _cached(tag,data,call)
def text_of(resp):
    out=[]
    for it in resp.get("output",[]):
        for c in it.get("content",[]) or []:
            if c.get("type")=="output_text": out.append(c["text"])
    return "".join(out)
def transcribe(wav_path, mode="DIARIZATION", keywords=None, tag="asr"):
    wav=pathlib.Path(wav_path).read_bytes()
    req={"model":"muse-voice-transcribe-1.0","mode":mode,"audioEncoding":"WAV"}
    if keywords: req["keywords"]=keywords
    def call():
        b="----metaval"+hashlib.md5(wav[:1000]).hexdigest()
        body=(f"--{b}\r\nContent-Disposition: form-data; name=\"request\"\r\nContent-Type: application/json\r\n\r\n{json.dumps(req)}\r\n"
              f"--{b}\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"a.wav\"\r\nContent-Type: audio/wav\r\n\r\n").encode()+wav+f"\r\n--{b}--\r\n".encode()
        r=urllib.request.Request(BASE+"/asr/transcribe",data=body,headers={"Authorization":"Bearer "+KEY,"Content-Type":f"multipart/form-data; boundary={b}","Accept":"application/json"})
        try: return json.load(urllib.request.urlopen(r,timeout=300))
        except urllib.error.HTTPError as e: return {"error":e.code,"body":e.read().decode()[:2000]}
    return _cached(tag+json.dumps(req),wav,call)
