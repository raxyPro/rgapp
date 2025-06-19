from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    print("Request args (query params):", request.args)
    print("Request form (POST data):", request.form)
    print("Request cookies:", request.cookies)
    print("Request headers:", dict(request.headers))
    headers=dict(request.headers)
    print(type(headers))
    #return headers
    #print("Request files:", request.files)
    
    return render_template('atest.html',headers=headers)
    """,
        args=request.args,
        form=request.form,
        cookies=request.cookies,
        headers=dict(request.headers),
        files=request.files
    )"""

if __name__ == '__main__':
    app.run(debug=True)