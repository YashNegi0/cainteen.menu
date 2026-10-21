import os
import sqlite3
from flask import Flask, g, render_template, request, redirect, url_for, jsonify, flash

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "canteen.db")
app = Flask(__name__)
app.secret_key = "canteen-center"


def init_db():
    if not os.path.exists(DB):
        c = sqlite3.connect(DB)
        c.executescript(open(os.path.join(BASE, "schema.sql")).read())
        c.commit()
        c.close()


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("pragma foreign_keys=on")
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


def q(sql, args=(), one=False):
    rows = db().execute(sql, args).fetchall()
    return (rows[0] if rows else None) if one else rows


def run(sql, args=()):
    c = db()
    cur = c.execute(sql, args)
    c.commit()
    return cur.lastrowid


def since(p):
    return {
        "today": "date('now','localtime')",
        "week": "date('now','localtime','-6 days')",
        "month": "date('now','localtime','-29 days')",
    }.get(p, "'0000-01-01'")


def guarded(action, back, ok):
    try:
        action()
        flash(ok, "ok")
    except sqlite3.IntegrityError as e:
        flash("Cannot save: " + ("duplicate value" if "UNIQUE" in str(e) else "record is in use"), "err")
    return redirect(url_for(back))


@app.get("/")
def dashboard():
    return render_template("dashboard.html")


@app.get("/api/income")
def api_income():
    rows = q(
        f"""select f.food_name n, sum(oi.quantity*oi.price) v from order_item oi
        join orders o on o.order_id=oi.order_id join food f on f.food_id=oi.food_id
        where o.status!='cancelled' and date(o.created_at)>={since(request.args.get('p'))}
        group by f.food_id order by v desc"""
    )
    labels = [r["n"] for r in rows[:5]]
    values = [r["v"] for r in rows[:5]]
    rest = sum(r["v"] for r in rows[5:])
    if rest:
        labels.append("Others")
        values.append(rest)
    return jsonify(labels=labels, values=values, total=sum(values))


@app.get("/api/orders")
def api_orders():
    r = q(f"select count(*) c from orders where status!='cancelled' and date(created_at)>={since(request.args.get('p'))}", one=True)
    return jsonify(value=r["c"])


@app.get("/api/customers")
def api_customers():
    r = q(f"select count(distinct student_id) c from orders where status!='cancelled' and date(created_at)>={since(request.args.get('p'))}", one=True)
    return jsonify(value=r["c"])


@app.get("/api/top")
def api_top():
    rows = q(
        f"""select f.food_name n, sum(oi.quantity) c from order_item oi
        join orders o on o.order_id=oi.order_id join food f on f.food_id=oi.food_id
        where o.status!='cancelled' and date(o.created_at)>={since(request.args.get('p'))}
        group by f.food_id order by c desc limit 5"""
    )
    return jsonify(rows=[dict(r) for r in rows])


@app.get("/api/daily")
def api_daily():
    rows = q(
        """select date(created_at) d, sum(total_amount) t from orders where status!='cancelled'
        group by d order by d desc limit 14"""
    )[::-1]
    return jsonify(labels=[r["d"] for r in rows], values=[r["t"] for r in rows])


@app.get("/pos")
def pos():
    foods = [dict(r) for r in q("select f.*, c.category_name from food f join category c using(category_id) order by f.food_name")]
    return render_template("pos.html", foods=foods, categories=q("select * from category order by category_id"), students=q("select * from student order by name"))


@app.post("/api/order")
def api_place_order():
    d = request.get_json(force=True)
    items = d.get("items") or []
    if not items:
        return jsonify(error="Cart is empty"), 400
    method = d.get("method", "cash")
    if method not in ("cash", "ewallet", "credit"):
        return jsonify(error="Invalid payment method"), 400
    c = db()
    try:
        lines, total = [], 0
        for i in items:
            f = c.execute("select * from food where food_id=?", (i["food_id"],)).fetchone()
            n = int(i["qty"])
            if not f or n < 1:
                raise ValueError("Invalid item")
            if f["stock"] < n:
                raise ValueError(f"Only {f['stock']} left of {f['food_name']}")
            lines.append((f["food_id"], n, f["price"]))
            total += n * f["price"]
        oid = c.execute("insert into orders(student_id,total_amount) values(?,?)", (d.get("student_id") or None, total)).lastrowid
        for fid, n, p in lines:
            c.execute("insert into order_item(order_id,food_id,quantity,price) values(?,?,?,?)", (oid, fid, n, p))
            c.execute("update food set stock=stock-? where food_id=?", (n, fid))
        c.execute("insert into payment(order_id,method,amount,status) values(?,?,?,?)", (oid, method, total, "unpaid" if method == "credit" else "paid"))
        c.commit()
    except ValueError as e:
        c.rollback()
        return jsonify(error=str(e)), 400
    return jsonify(order_id=oid, total=total)


@app.route("/students", methods=["GET", "POST"])
def students():
    if request.method == "POST":
        f = request.form
        return guarded(lambda: run("insert into student(name,email) values(?,?)", (f["name"].strip(), f["email"].strip())), "students", "Student added")
    rows = q(
        """select s.*, count(o.order_id) orders, coalesce(sum(case when o.status!='cancelled' then o.total_amount end),0) spent
        from student s left join orders o using(student_id) group by s.student_id order by s.name"""
    )
    return render_template("students.html", rows=rows)


@app.post("/students/<int:i>/edit")
def student_edit(i):
    f = request.form
    return guarded(lambda: run("update student set name=?, email=? where student_id=?", (f["name"].strip(), f["email"].strip(), i)), "students", "Student updated")


@app.post("/students/<int:i>/delete")
def student_delete(i):
    return guarded(lambda: run("delete from student where student_id=?", (i,)), "students", "Student deleted")


@app.route("/categories", methods=["GET", "POST"])
def categories():
    if request.method == "POST":
        return guarded(lambda: run("insert into category(category_name) values(?)", (request.form["name"].strip(),)), "categories", "Category added")
    rows = q("select c.*, count(f.food_id) foods from category c left join food f using(category_id) group by c.category_id order by c.category_id")
    return render_template("categories.html", rows=rows)


@app.post("/categories/<int:i>/edit")
def category_edit(i):
    return guarded(lambda: run("update category set category_name=? where category_id=?", (request.form["name"].strip(), i)), "categories", "Category updated")


@app.post("/categories/<int:i>/delete")
def category_delete(i):
    return guarded(lambda: run("delete from category where category_id=?", (i,)), "categories", "Category deleted")


@app.route("/items", methods=["GET", "POST"])
def items():
    if request.method == "POST":
        f = request.form
        return guarded(
            lambda: run("insert into food(category_id,food_name,price,stock) values(?,?,?,?)", (f["category_id"], f["name"].strip(), f["price"], f["stock"])),
            "items",
            "Item added",
        )
    rows = q("select f.*, c.category_name from food f join category c using(category_id) order by c.category_name, f.food_name")
    return render_template("items.html", rows=rows, categories=q("select * from category order by category_name"))


@app.post("/items/<int:i>/edit")
def item_edit(i):
    f = request.form
    return guarded(
        lambda: run("update food set category_id=?, food_name=?, price=?, stock=? where food_id=?", (f["category_id"], f["name"].strip(), f["price"], f["stock"], i)),
        "items",
        "Item updated",
    )


@app.post("/items/<int:i>/delete")
def item_delete(i):
    return guarded(lambda: run("delete from food where food_id=?", (i,)), "items", "Item deleted")


@app.get("/orders")
def orders():
    st = request.args.get("status", "")
    rows = q(
        f"""select o.*, s.name student, p.method, p.status pay_status,
        group_concat(f.food_name || ' x' || oi.quantity, ', ') lines
        from orders o left join student s using(student_id)
        left join payment p using(order_id)
        join order_item oi using(order_id) join food f using(food_id)
        {'where o.status=?' if st else ''} group by o.order_id order by o.order_id desc""",
        (st,) if st else (),
    )
    return render_template("orders.html", rows=rows, st=st)


@app.post("/orders/<int:i>/status")
def order_status(i):
    new = request.form["status"]
    old = q("select status from orders where order_id=?", (i,), one=True)
    c = db()
    if old and old["status"] != new:
        if new == "cancelled":
            c.execute("update food set stock=stock+(select quantity from order_item where order_id=? and food_id=food.food_id) where food_id in (select food_id from order_item where order_id=?)", (i, i))
        elif old["status"] == "cancelled":
            c.execute("update food set stock=max(0,stock-(select quantity from order_item where order_id=? and food_id=food.food_id)) where food_id in (select food_id from order_item where order_id=?)", (i, i))
        c.execute("update orders set status=? where order_id=?", (new, i))
        if new == "completed":
            c.execute("update payment set status='paid', paid_at=datetime('now','localtime') where order_id=?", (i,))
        c.commit()
        flash(f"Order #{i} marked {new}", "ok")
    return redirect(request.referrer or url_for("orders"))


@app.get("/reports")
def reports():
    a = request.args.get("from", "")
    b = request.args.get("to", "")
    w = "o.status!='cancelled' and date(o.created_at) between ? and ?"
    args = (a or "0000-01-01", b or "9999-12-31")
    summary = q(f"select count(*) n, coalesce(sum(total_amount),0) t from orders o where {w}", args, one=True)
    by_cat = q(
        f"""select c.category_name n, sum(oi.quantity) qty, sum(oi.quantity*oi.price) t from order_item oi
        join orders o using(order_id) join food f using(food_id) join category c using(category_id)
        where {w} group by c.category_id order by t desc""",
        args,
    )
    by_pay = q(f"select p.method n, count(*) qty, sum(p.amount) t from payment p join orders o using(order_id) where {w} group by p.method order by t desc", args)
    low = q("select f.food_name, f.stock, c.category_name from food f join category c using(category_id) where f.stock<=10 order by f.stock")
    return render_template("reports.html", summary=summary, by_cat=by_cat, by_pay=by_pay, low=low, a=a, b=b)


init_db()

if __name__ == "__main__":
    app.run(debug=True)
