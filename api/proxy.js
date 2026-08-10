// api/proxy.js
export default async function handler(req, res) {
  const targetUrl = req.query.url;
  if (!targetUrl) return res.status(400).send("缺少url参数");
  try {
    const resp = await fetch(targetUrl, {
      method: req.method,
      headers: {
        "Content-Type": req.headers["content-type"] || "application/json"
      },
      body: req.method !== "GET" ? JSON.stringify(req.body) : undefined
    });
    const data = await resp.json();
    res.setHeader("Access‑Control‑Allow‑Origin", "*");
    return res.status(resp.status).json(data);
  } catch (err) {
    return res.status(500).json({error: err.message});
  }
}
