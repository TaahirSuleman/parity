import json, asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={"width":1280,"height":720})
        await pg.goto("file:///path/to/parity/store/checkout.html")
        await pg.add_script_tag(path="node_modules/axe-core/axe.min.js")
        r=await pg.evaluate("axe.run(document,{resultTypes:['violations']})")
        await pg.screenshot(path="checkout.png")
        cdp=await pg.context.new_cdp_session(pg); ax=await cdp.send("Accessibility.getFullAXTree")
        nodes=[{"role":n.get("role",{}).get("value"),"name":n.get("name",{}).get("value"),"backendId":n.get("backendDOMNodeId")} for n in ax["nodes"] if not n.get("ignored") and n.get("role",{}).get("value") not in ("generic","none","InlineTextBox","StaticText","LineBreak","RootWebArea")]
        for n in nodes:
            try:
                bm=await cdp.send("DOM.getBoxModel",{"backendNodeId":n["backendId"]}); q=bm["model"]["border"]
                n["bbox_0_1000"]=[round(q[0]/1.28),round(q[1]/0.72),round(q[4]/1.28),round(q[5]/0.72)]
            except Exception: pass
        ids=await pg.evaluate("""()=>Object.fromEntries(['f1','f2','f4','f5','f6','c1','c2','card'].map(i=>{const r=document.getElementById(i).getBoundingClientRect();return [i,[Math.round(r.left/1.28),Math.round(r.top/0.72),Math.round(r.right/1.28),Math.round(r.bottom/0.72)]]}))""")
        json.dump({"axe_violations":[{"id":v["id"],"targets":[t["target"] for t in v["nodes"]]} for v in r["violations"]],"ax_tree":nodes,"seeded_boxes":ids},open("audit_truth.json","w"),indent=1)
        await b.close()
asyncio.run(main())
d=json.load(open("audit_truth.json")); print("axe violations:",json.dumps(d["axe_violations"])); print("ax nodes:",[(n["role"],n["name"]) for n in d["ax_tree"]])
