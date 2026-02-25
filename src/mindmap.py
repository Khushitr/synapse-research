"""
mindmap.py — Renders an interactive mind map using vis.js Network.
Returns an HTML string to embed in st.components.v1.html()
"""

def render_mindmap_html(mindmap_data: dict) -> str:
    """
    Takes mindmap_data: {center: str, branches: [{label, children: [str]}]}
    Returns full HTML page with interactive vis.js Network mind map.
    """
    center = mindmap_data.get("center", "Research Topic")
    branches = mindmap_data.get("branches", [])

    # Build nodes and edges
    nodes = [{"id": 0, "label": center, "group": "center", "level": 0}]
    edges = []
    node_id = 1

    colors = ["#7c6af7", "#60a5fa", "#34d399", "#f59e0b", "#f87171", "#a78bfa"]

    for i, branch in enumerate(branches):
        color = colors[i % len(colors)]
        b_id = node_id
        nodes.append({
            "id": b_id,
            "label": branch["label"],
            "group": f"branch_{i}",
            "level": 1,
            "color": color
        })
        edges.append({"from": 0, "to": b_id})
        node_id += 1

        for child in branch.get("children", []):
            c_id = node_id
            nodes.append({
                "id": c_id,
                "label": child[:35],
                "group": f"leaf_{i}",
                "level": 2,
                "color": color + "88"
            })
            edges.append({"from": b_id, "to": c_id})
            node_id += 1

    import json
    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background: #0c0c0e; font-family: 'Inter', sans-serif; }}
  #mindmap {{ width:100%; height:500px; border:1px solid #1c1c26; border-radius:12px; }}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/vis-network.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/dist/vis-network.min.css">
</head>
<body>
<div id="mindmap"></div>
<script>
var nodes = new vis.DataSet({nodes_json});
var edges = new vis.DataSet({edges_json});

var options = {{
  nodes: {{
    shape: "box",
    borderWidth: 0,
    borderWidthSelected: 2,
    font: {{ color: "#e8eaf0", size: 13, face: "Inter, Arial" }},
    margin: {{ top: 10, bottom: 10, left: 14, right: 14 }},
    shadow: {{ enabled: true, color: "rgba(0,0,0,0.5)", size: 8, x: 2, y: 2 }},
  }},
  edges: {{
    color: {{ color: "#252535", highlight: "#7c6af7" }},
    width: 1.5,
    smooth: {{ type: "cubicBezier", forceDirection: "none", roundness: 0.5 }},
    arrows: {{ to: {{ enabled: false }} }}
  }},
  groups: {{
    center: {{
      color: {{ background: "#4f47d4", border: "#7c6af7" }},
      font: {{ size: 16, bold: true, color: "#fff" }},
      shape: "ellipse",
      margin: 16
    }}
  }},
  layout: {{
    hierarchical: {{ enabled: false }},
    randomSeed: 42
  }},
  physics: {{
    enabled: true,
    repulsion: {{ nodeDistance: 180, springLength: 200, springConstant: 0.04 }},
    solver: "repulsion",
    stabilization: {{ iterations: 200 }}
  }},
  interaction: {{
    hover: true,
    zoomView: true,
    dragView: true
  }},
  background: {{ color: "#0c0c0e" }}
}};

var container = document.getElementById("mindmap");
var data = {{ nodes: nodes, edges: edges }};
var network = new vis.Network(container, data, options);
network.once("stabilized", function() {{
  network.fit({{ animation: {{ duration: 600, easingFunction: "easeInOutQuad" }} }});
}});
</script>
</body>
</html>"""