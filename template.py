import base64, os
from jinja2 import Template

template_str = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Task Execution Report</title>
    <style>
        body{font-family:Arial,sans-serif;line-height:1.6;margin:20px;color:#333}
        .example{border:1px solid #ddd;border-radius:8px;margin-bottom:30px;padding:15px;
                 box-shadow:0 2px 4px rgba(0,0,0,0.1)}
        h1{color:#1a5dad;border-bottom:3px solid #3e7dcc;padding-bottom:12px;margin-bottom:25px}
        h2{color:#0c3b7d;font-size:22px;border-left:4px solid #5990d5;padding-left:10px;margin:20px 0 15px}
        .badge{display:inline-block;padding:2px 6px;border-radius:4px;font-size:.8em;color:#fff}
        .action{background:#4096ff}.plan{background:#faad14}
        .kv{margin-bottom:8px}
        .kv b{display:inline-block;width:90px}
        .screenshot {
            margin: 20px 0;
            clear: both;
            page-break-inside: avoid;
        }
        .screenshot img {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .content-section {
            margin: 20px 0;
            clear: both;
            page-break-inside: avoid;
        }
    </style>
</head>
<body>
    <h1>Task Execution Report</h1>
    
    {% for example in examples %}
    <div class="example">
        <!-- Head：step_id + mode -->
        <h2>
           Step&nbsp;{{ example.step_id }}&nbsp;
           {% if example.mode == 'action' %}
             <span class="badge action">action</span>
           {% else %}
             <span class="badge plan">planning</span>
           {% endif %}
        </h2>
        
        <p class="kv"><b>Thought:</b>{{ example.thought or '(none)' }}</p>
        <p class="kv"><b>Operation:</b>{{ example.operation or '(none)' }}</p>
        <p class="kv"><b>Action:</b>{{ example.action or '(none)' }}</p>

        {% if example.screenshot %}
        <div class="screenshot">
            <h3>Screenshot</h3>
            <img src="{{ example.screenshot }}" alt="Screenshot">
        </div>
        {% endif %}

        {% if example.memory %}
        <div class="content-section important_notes">
            <h3>Memory</h3>
            <p>{{ example.memory }}</p>
        </div>
        {% endif %}

        {% if example.reflection %}
          <div class="content-section finish_thought">
              <h3>Reflection</h3><p>{{ example.reflection }}</p>
          </div>
        {% elif example.planning %}
          <div class="content-section finish_thought">
              <h3>Planning</h3><p>{{ example.planning }}</p>
          </div>
        {% endif %}
    </div>
    {% endfor %}
</body>
</html>"""

template = Template(template_str)


def image_to_base64(image_path):
    if image_path is None or not os.path.exists(image_path):
        return ""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = image_path.lower().split(".")[-1]
    if ext not in ("jpg", "jpeg", "png"):
        ext = "jpeg"
    return f"data:image/{ext};base64,{b64}"
