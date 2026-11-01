import sys; sys.path.insert(0,".."); import meta, json, base64, asyncio, time
from playwright.async_api import async_playwright
GOAL="On this checkout page, change the card Expiry field to 10/28, then press the pay button. Stop when the order is confirmed."
async def main():
    log=[]; t0=time.time()
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={"width":1280,"height":720})
        await pg.goto("file:///path/to/parity/store/checkout.html")
        shot=lambda: pg.screenshot()
        img="data:image/png;base64,"+base64.b64encode(await shot()).decode()
        body={"model":"muse-spark-1.3","tools":[{"type":"computer"}],"reasoning":{"effort":"low"},"truncation":"auto",
              "input":[{"role":"user","content":[{"type":"input_text","text":GOAL},{"type":"input_image","image_url":img}]}]}
        prev=None; tokens=0
        for turn in range(12):
            if prev: body={"model":"muse-spark-1.3","tools":[{"type":"computer"}],"reasoning":{"effort":"low"},"previous_response_id":prev,"input":out_items}
            o=meta.responses(body,tag=f"a1b-{turn}-{prev}")
            if "body" in o: log.append({"turn":turn,"error":o["body"][:400]}); break
            prev=o["id"]; tokens+=o.get("usage",{}).get("total_tokens",0)
            calls=[it for it in o.get("output",[]) if it.get("type")=="computer_call"]
            if not calls: log.append({"turn":turn,"final":meta.text_of(o)[:200]}); break
            out_items=[]
            for c in calls:
                acts=c.get("actions") or ([c["action"]] if c.get("action") else [])
                for a in acts:
                    ty=a.get("type"); log.append({"turn":turn,"action":a})
                    if ty in("click","double_click"): await (pg.mouse.dblclick if ty=="double_click" else pg.mouse.click)(a["x"],a["y"])
                    elif ty=="type": await pg.keyboard.type(a["text"])
                    elif ty=="keypress":
                        M={"CTRL":"Control","CONTROL":"Control","ENTER":"Enter","BACKSPACE":"Backspace","CMD":"Meta","SHIFT":"Shift","HOME":"Home","END":"End","TAB":"Tab","ALT":"Alt"}
                        await pg.keyboard.press("+".join(M.get(k.upper(),k) for k in a.get("keys",[])))
                    elif ty=="scroll": await pg.mouse.wheel(a.get("scroll_x",0),a.get("scroll_y",0))
                    elif ty=="wait": await asyncio.sleep(1)
                img="data:image/png;base64,"+base64.b64encode(await shot()).decode()
                out_items.append({"type":"computer_call_output","call_id":c["call_id"],"acknowledged_safety_checks":c.get("pending_safety_checks",[]),
                                  "output":{"type":"computer_screenshot","image_url":img}})
        ok=await pg.is_visible("#done"); exp=await pg.input_value("#exp"); await b.close()
    r={"success":ok,"expiry_value":exp,"turns":len({l["turn"] for l in log}),"tokens":tokens,"seconds":round(time.time()-t0,1),"log":log}
    json.dump(r,open("../results/a1_computer_use.json","w"),indent=1); print(json.dumps({k:r[k] for k in ("success","expiry_value","turns","tokens","seconds")})); print(json.dumps(log)[:1500])
asyncio.run(main())
