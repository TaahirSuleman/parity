import sys; sys.path.insert(0,".."); import meta, json, base64
d=json.load(open("audit_truth.json"))
tree=[{k:n.get(k) for k in ("role","name","bbox_0_1000")} for n in d["ax_tree"] if n["role"] not in ("banner","main","region","paragraph","LabelText")]
P=("You audit a web page for accessibility gaps that rule engines miss. You get (1) a screenshot of what a sighted user sees and (2) the accessibility tree "
   "(what a screen-reader user hears: role + accessible name, with boxes on a normalized 0-1000 grid). Find every place where a sighted user and a screen-reader "
   "user would get materially different information or actions: wrong/meaningless names, information only in pixels (images, canvas, colour), names contradicting visible text or icon meaning. "
   "Do not flag elements that are fine.\n"
   'Answer only JSON: {"findings":[{"what_sighted_user_sees":"...","what_screen_reader_says":"...","why_it_matters":"...","bbox":{"x_min":0,"y_min":0,"x_max":0,"y_max":0}}]}\n\nACCESSIBILITY TREE:\n'+json.dumps(tree))
img="data:image/png;base64,"+base64.b64encode(open("checkout.png","rb").read()).decode()
o=meta.responses({"model":"muse-spark-1.3","reasoning":{"effort":"medium"},"text":{"format":{"type":"json_object"}},"max_output_tokens":6000,
   "input":[{"role":"user","content":[{"type":"input_text","text":P},{"type":"input_image","image_url":img}]}]},tag="a2-checkout")
j=json.loads(meta.text_of(o)); S=d["seeded_boxes"]
def hit(bb,box): cx=(bb["x_min"]+bb["x_max"])/2; cy=(bb["y_min"]+bb["y_max"])/2; return box[0]-15<=cx<=box[2]+15 and box[1]-15<=cy<=box[3]+15
seeded={"f1":"alt=image on 50% OFF banner","f2":"price on canvas","card":"red-border error, no text","f4":"Terms vs Click here","f5":"Pay R1,249 vs Submit","f6":"trash icon vs Close"}
found={k:any(hit(f["bbox"],S[k]) for f in j["findings"] if f.get("bbox")) for k in seeded}
fp=[f["what_sighted_user_sees"] for f in j["findings"] if not any(hit(f["bbox"],S[k]) for k in seeded if k in S)]
ctrl={k:any(hit(f["bbox"],S[k]) for f in j["findings"] if f.get("bbox")) for k in ("c1","c2")}
out={"seeded_found_by_box":found,"found_n":sum(found.values()),"unmatched_findings":fp,"controls_flagged":ctrl,"tokens":o.get("usage",{}).get("total_tokens"),"lat":o.get("_latency_s"),"findings":j["findings"]}
json.dump(out,open("../results/a2_divergence.json","w"),indent=1)
print(json.dumps({k:out[k] for k in ("seeded_found_by_box","found_n","unmatched_findings","controls_flagged","tokens","lat")},indent=1))
for f in j["findings"]: print("-",f["what_sighted_user_sees"][:60],"|",f["what_screen_reader_says"][:50])
