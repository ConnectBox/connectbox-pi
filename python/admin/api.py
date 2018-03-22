import os

from flask import Flask,request,abort

def get_property(property):
    #if not request.json:
    #    abort(400) # bad request
    return "get " + property


def set_property(property):
    #if not request.json:
    #    abort(400) # bad request
    return "set " + property


def register(app):
    app.add_url_rule(
        rule='/admin/api/<property>',
        endpoint='get_property',
        methods=['GET'],
        view_func=get_property)
    app.add_url_rule(
        rule='/admin/api/<property>',
        endpoint='set_property',
        methods=['PUT','POST'],
        view_func=set_property)
