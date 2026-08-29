import pandas as pd
import json
import datetime
import html


def is_json_empty(json_obj):
    # return true if length is 0.
    return len(json_obj) == 0



class imbursement:
   
   
   def __init__(self, id , amount, date):
      self.amount =  amount
      self.date = date
      self.id = id


class expense:
  def __init__(self, amount, id, date, event_name, expense_type):
    self.amount =  amount
    self.date = date
    self.event_name = event_name
    self.id = id
    self.expense_type = expense_type


 
with open("data.json","r") as file:
    data = json.load(file)
    if is_json_empty(data):
        data = {"budget": 0,"expenses": 0, "imbursements_history" : [], "expense_history" : []}


def reset():
   with open("data.json","w") as file:
        data = {"budget": 0,"expenses": 0, "imbursements_history" : [], "expense_history" : []}
        json.dump(data, file)

def save():
    with open("data.json","w") as file:
       json.dump(data, file)


def add_budget(amount, date, id):
      
      data["budget"] += amount
      data["imbursements_history"].append(imbursement(id,amount,date))
     


def decrease_budget(id,amount, date, event_name):
   if  data["budget"]  >= amount:
      data["budget"] -= amount
      data["expenses"] += amount
      data["expenses_history"].append(expense(id,amount,date,event_name))

def display_imburse_history():
   
   df_imburse = pd.DataFrame({"id":[],"amount":[],"date" : []})
   for i in data["imbursements_history"]:
      new_row = pd.DataFrame([{"id":i.id,"amount":i.amount,"date":i.date}])
      df_imburse = pd.concat([df_imburse,new_row])
   return df_imburse

def display_expense_history():
   
   df_expense = pd.DataFrame({"id":[],"amount":[],"date" : [], "event_name":[], "event_type":[]})
   for i in data["expense_history"]:
      new_row = pd.DataFrame([{"id":i.id,"amount":i.amount,"date":i.date,"event_name":i.event_name, "expense_type":i.expense_type}])
      df_expense = pd.concat([df_expense,new_row])

   return df_expense

def display_expense_graph():
   df_expense = pd.DataFrame({"id":[],"amount":[],"date" : [], "event_name":[], "event_type":[]})
   for i in data["expense_history"]:
      new_row = pd.DataFrame([{"id":i.id,"amount":i.amount,"date":i.date,"event_name":i.event_name, "expense_type":i.expense_type}])
      df_expense = pd.concat([df_expense,new_row])
   
   return df_expense.groupby()
