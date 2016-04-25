#!/usr/bin/env python
# -*- coding=UTF-8 -*-
# *************************************************************************
#   Copyright © 2015 JiangLin. All rights reserved.
#   File Name: __init__.py
#   Author:JiangLin
#   Mail:xiyang0807@gmail.com
#   Created Time: 2015-11-18 08:03:11
# *************************************************************************
from flask import (Flask, render_template, send_from_directory, request,
                   Markup, g)
from flask.json import JSONEncoder
from flask_assets import Environment, Bundle
from flask_mail import Mail
from flask_login import LoginManager, current_user
from flask_principal import Principal
from config import load_config
from misaka import Markdown, HtmlRenderer
from flask_sqlalchemy import SQLAlchemy
from redis import StrictRedis
from flask_cache import Cache
from flask_babel import Babel
from flask_babel import lazy_gettext as _
from flask_maple import MapleBootstrap


def create_app():
    app = Flask(__name__, static_folder='static')
    config = load_config()
    app.config.from_object(config)
    return app


def register(app):
    register_routes(app)
    # register_assets(app)
    # register_form(app)
    register_jinja2(app)
    register_db(app)
    register_maple(app)


def register_maple(app):
    maple = MapleBootstrap(css=('style/honmaple.css',))
    maple.init_app(app)


def register_routes(app):
    from maple.index.views import site
    app.register_blueprint(site, url_prefix='')
    from maple.auth.views import site
    app.register_blueprint(site, url_prefix='')
    from maple.user.views import site
    app.register_blueprint(site, url_prefix='/u')
    from maple.blog.views import site
    app.register_blueprint(site, url_prefix='/blog')
    from maple.question.views import site
    app.register_blueprint(site, url_prefix='/question')
    from maple.books.views import site
    app.register_blueprint(site, url_prefix='/books')
    import maple.admin.admin
    # from maple.admin.views import site
    # app.register_blueprint(site, url_prefix='/admin')


def register_form(app):
    from flask_wtf.csrf import CsrfProtect
    csrf = CsrfProtect()
    csrf.init_app(app)


def register_jinja2(app):
    def safe_markdown(text):
        html = HtmlRenderer()
        markdown = Markdown(html)
        return Markup(markdown(text))

    def visit_total(article_id):
        '''文章浏览次数'''
        from maple.main.mark_record import get_article_count
        return get_article_count(article_id)

    def last_online_time(ip):
        from maple.main.mark_record import get_user_last_activity
        ip = str(ip, 'utf-8')
        return get_user_last_activity(ip)

    def visited_time(ip):
        from maple.main.mark_record import get_visited_time
        ip = str(ip, 'utf-8')
        return get_visited_time(ip)

    def visited_last_time(ip):
        from maple.main.mark_record import get_visited_last_time
        ip = str(ip, 'utf-8')
        return get_visited_last_time(ip)

    def visited_pages(ip):
        from maple.main.mark_record import get_visited_pages
        ip = str(ip, 'utf-8')
        return get_visited_pages(ip)

    def query_ip(ip):
        from IP import find
        return find(ip)

    app.jinja_env.filters['safe_markdown'] = safe_markdown
    app.jinja_env.filters['visit_total'] = visit_total
    app.jinja_env.filters['last_online_time'] = last_online_time
    app.jinja_env.filters['visited_time'] = visited_time
    app.jinja_env.filters['visited_last_time'] = visited_last_time
    app.jinja_env.filters['visited_pages'] = visited_pages
    app.jinja_env.filters['query_ip'] = query_ip
    app.jinja_env.add_extension('jinja2.ext.loopcontrols')


def register_assets(app):
    bundles = {
        'home_js': Bundle('style/js/jquery.min.js',
                          'style/js/bootstrap.min.js',
                          'style/honmaple.js',
                          output='style/assets/home.js',
                          filters='jsmin'),
        'home_css': Bundle('style/css/bootstrap.min.css',
                           'style/honmaple.css',
                           output='style/assets/home.css',
                           filters='cssmin')
    }

    assets = Environment(app)
    assets.register(bundles)


def register_login(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.session_protection = "strong"
    # login_manager.login_message = gettext(u"这个页面要求登陆，请登陆")
    login_manager.login_message = _("Please login to access this page.")

    return login_manager


def register_db(app):
    db.init_app(app)


def register_redis(app):
    config = app.config
    redis_data = StrictRedis(db=config['CACHE_REDIS_DB'],
                             password=config['CACHE_REDIS_PASSWORD'])
    return redis_data


def register_cache(app):
    cache = Cache(config={'CACHE_TYPE': 'null'})
    cache.init_app(app)
    return cache


app = create_app()
db = SQLAlchemy()
mail = Mail(app)
principals = Principal(app)
login_manager = register_login(app)
redis_data = register_redis(app)
cache = register_cache(app)
babel = Babel(app)
register(app)


class CustomJSONEncoder(JSONEncoder):
    """This class adds support for lazy translation texts to Flask's
    JSON encoder. This is necessary when flashing translated texts."""

    def default(self, obj):
        from speaklater import is_lazy_string
        if is_lazy_string(obj):
            try:
                return unicode(obj)  # python 2
            except NameError:
                return str(obj)  # python 3
        return super(CustomJSONEncoder, self).default(obj)


app.json_encoder = CustomJSONEncoder


@app.before_request
def before_request():
    from maple.main.mark_record import allow_ip, mark_online, mark_visited
    from maple.blog.forms import SearchForm
    allow_ip(request.remote_addr)
    g.search_form = SearchForm()
    g.user = current_user
    mark_online(request.remote_addr)
    if '/static/' in request.path:
        pass
    elif '/favicon.ico' in request.path:
        pass
    elif '/robots.txt' in request.path:
        pass
    else:
        path = request.path
        mark_visited(request.remote_addr, path)


@app.errorhandler(404)
def not_found(error):
    return render_template('templet/error_404.html'), 404


@app.errorhandler(500)
def error(error):
    return render_template('templet/error_500.html'), 500


@app.route('/robots.txt')
@app.route('/favicon.ico')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])
