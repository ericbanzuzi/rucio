#!/usr/bin/env python
# Copyright European Organization for Nuclear Research (CERN) since 2012
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from flask import Blueprint, make_response, render_template, request

from rucio.common.config import config_get_bool
from rucio.common.constants import DEFAULT_VO
from rucio.common.policy import get_policy
from rucio.gateway.authentication import get_auth_token_x509
from rucio.web.rest.flaskapi.v1.common import generate_http_error_flask
from rucio.web.ui.flask.common.utils import AUTH_ISSUERS, SAML_SUPPORT, USERPASS_SUPPORT, authenticate, finalize_auth, get_token, oidc_auth, saml_auth, userpass_auth, x509token_auth

MULTI_VO = config_get_bool('common', 'multi_vo', raise_exception=False, default=False)
POLICY = get_policy()
ATLAS_URLS = ()
OTHER_URLS = ()


def auth():
    auth_type = request.cookies.get('x-rucio-auth-type')
    if str(auth_type).lower() == 'x509':
        token = get_token(get_auth_token_x509)
        if token:
            response = make_response()
            response.headers['X-Rucio-Auth-Token'] = token
            print("auth()")
            print(token)
            return response
        else:
            return generate_http_error_flask(401, 'CannotAuthenticate', 'Cannot get token')
    else:
        return render_template('select_login_method.html', oidc_issuers=AUTH_ISSUERS, saml_support=SAML_SUPPORT, userpass_support=USERPASS_SUPPORT)


def login():
    if request.method == 'GET':
        account = request.args.get('account')
        vo = request.args.get('vo')
        return render_template('login.html', account=account, vo=vo, userpass_support=USERPASS_SUPPORT)
    if request.method == 'POST':
        return userpass_auth()


def oidc():
    account = request.args.get('account')
    issuer = request.args.get('issuer')
    vo = request.args.get('vo')
    if not MULTI_VO:
        vo = DEFAULT_VO

    if not issuer:
        return generate_http_error_flask(401, 'CannotAuthenticate', 'Cannot get token OIDC auth url from the server.')

    return oidc_auth(account, issuer, vo)


def oidc_final():
    session_token = request.cookies.get('x-rucio-auth-token')
    return finalize_auth(session_token, 'OIDC')


def saml():
    return saml_auth(request.method)


def x509():
    return x509token_auth()


AUTH_URLS = (
    ('/auth', 'auth', auth, ['GET', ]),
    ('/login', 'login', login, ['GET', 'POST']),
    ('/oidc', 'oidc', oidc, ['GET', ]),
    ('/oidc_final', 'oidc_final', oidc_final, ['GET', ]),
    ('/saml', 'saml', saml, ['GET', 'POST']),
    ('/x509', 'x509', x509, ['GET', ])
)

COMMON_URLS = (
    ('/account_rse_usage', 'account_rse_usage', 'Account RSE Usage'),
    ('/account', 'account', 'Account'),
    ('/bad_replicas', 'bad_replicas', 'Bad Replicas'),
    ('/bad_replicas/summary', 'bad_replicas_summary', 'Bad Replica Summary'),
    ('/did', 'did', 'Data Identifier'),
    ('/heartbeats', 'heartbeats', 'Heartbeats'),
    ('/lifetime_exception', 'lifetime_exception', 'Lifetime Exception'),
    ('/list_lifetime_exceptions', 'list_lifetime_exceptions', 'Lifetime Exception'),
    ('/list_accounts', 'accounts', 'Accounts'),
    ('/r2d2/approve', 'approve_rules', 'Rules in Approval State'),
    ('/r2d2/request', 'request_rule', 'Rucio Rule Definition Droid - Request Rule'),
    ('/r2d2/manage_quota', 'rse_account_usage', 'Manage Quota'),
    ('/r2d2', 'list_rules', 'Rucio Rule Definition Droid - List Rules'),
    ('/rse', 'rse', 'RSE Info'),
    ('/rse/protocol/add', 'rse_add_protocol', 'RSE Protocol'),
    ('/rses', 'rses', 'RSEs'),
    ('/rses/add', 'add_rse', 'Add RSE'),
    ('/rse_usage', 'rse_usage', 'RSE Usage'),
    ('/rse_locks', 'rse_locks', 'RSE Locks'),
    ('/rule', 'rule', 'Rule'),
    ('/rules', 'rules', 'Rules'),
    ('/search', 'search', 'Search'),
    ('/subscriptions/rules', 'subscriptionrules', 'Rules for Subscription'),
    ('/subscription', 'subscription', 'Subscription'),
    ('/subscriptions', 'subscriptions', 'Subscriptions'),
    ('/subscriptions_editor', 'subscriptions_editor', 'Subscriptions editor'),
    ('/suspicious_replicas', 'suspicious_replicas', 'Suspicious Replicas'),
    # TODO: add logfile extraction endpoints
    # ('/logfiles/load', 'load_logfile', load_logfile),
    # ('/logfiles/extract', 'extract_logfile', extract_logfile)
)

if POLICY == 'atlas':
    ATLAS_URLS = (
        ('/', 'atlas_index', 'Index'),
        ('/account_usage', 'account_usage', 'Group Account Usage'),
        ('/account_usage_history', 'account_usage_history', 'Account Usage History'),
        ('/dumps', 'dumps', 'Dumps'),
        ('/accounting', 'accounting', 'Accounting'),
        ('/conditions_summary', 'cond', 'ConditionsDB Summary'),
        ('/dbrelease_summary', 'dbrelease', 'DBRelease Summary'),
        ('/infrastructure', 'infrastructure', 'Infrastucture'),
        ('/rule_backlog_monitor', 'backlog_mon', 'Rules Backlog Monitoring')
    )
else:
    OTHER_URLS = (
        ('/', 'index', 'Index'),
    )


def view_maker(template, title):
    return lambda: authenticate(template=template, title=title)


def blueprint():
    bp = Blueprint('webui', __name__)

    for rule, endpoint, title in COMMON_URLS:
        template = endpoint + '.html'
        bp.add_url_rule(rule=rule, endpoint=endpoint, view_func=view_maker(template, title))

    for rule, endpoint, title in ATLAS_URLS:
        template = endpoint + '.html'
        bp.add_url_rule(rule=rule, endpoint=endpoint, view_func=view_maker(template, title))

    for rule, endpoint, title in OTHER_URLS:
        template = endpoint + '.html'
        bp.add_url_rule(rule=rule, endpoint=endpoint, view_func=view_maker(template, title))

    for rule, endpoint, view_func, methods in AUTH_URLS:
        bp.add_url_rule(rule=rule, endpoint=endpoint, view_func=view_func, methods=methods)

    return bp
