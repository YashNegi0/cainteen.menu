create table student(
  student_id integer primary key autoincrement,
  name text not null,
  email text not null unique
);
create table category(
  category_id integer primary key autoincrement,
  category_name text not null unique
);
create table food(
  food_id integer primary key autoincrement,
  category_id integer not null references category(category_id),
  food_name text not null,
  price real not null check(price >= 0),
  stock integer not null default 0 check(stock >= 0)
);
create table orders(
  order_id integer primary key autoincrement,
  student_id integer references student(student_id),
  total_amount real not null,
  status text not null default 'pending' check(status in ('pending','preparing','completed','cancelled')),
  created_at text not null default (datetime('now','localtime'))
);
create table order_item(
  item_id integer primary key autoincrement,
  order_id integer not null references orders(order_id) on delete cascade,
  food_id integer not null references food(food_id),
  quantity integer not null check(quantity > 0),
  price real not null
);
create table payment(
  payment_id integer primary key autoincrement,
  order_id integer not null unique references orders(order_id) on delete cascade,
  method text not null check(method in ('cash','ewallet','credit')),
  amount real not null,
  status text not null default 'paid' check(status in ('paid','unpaid')),
  paid_at text not null default (datetime('now','localtime'))
);

insert into category(category_name) values ('Breakfast'),('Lunch'),('Snacks'),('Dinner'),('Drinks');
insert into student(name,email) values ('Aarav Sharma','aarav@college.edu'),('Meera Joshi','meera@college.edu'),('Rohan Verma','rohan@college.edu');
insert into food(category_id,food_name,price,stock) values
(1,'Sausage and Bacon',350,20),(1,'Boiled Egg',25,60),(1,'Chocolate Donut',60,40),
(2,'Noodles',120,30),(2,'Allu Paratha',180,25),(2,'Mutton Biryani',450,15),
(3,'Chicken Roll',210,30),(3,'Momo',120,40),(3,'Burger and Fries',150,25),
(4,'Salmon with Veges',350,12),
(5,'Coke',60,80),(5,'Milk Coffee',80,50);
