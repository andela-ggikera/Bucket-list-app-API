from flask.ext.api import FlaskAPI
from flask import request
from models import db, BucketList, BucketListItem
from flask.ext.api.exceptions import \
    AuthenticationFailed, NotFound, ParseError, NotAcceptable
from exceptions.handler import CredentialsRequired
import auth


def create_app(module='instance.config.DevelopmentConfig'):
    """ Wrap the routes into one exportable method """
    app = FlaskAPI(__name__, instance_relative_config=True)
    # Object-based configuration
    app.config.from_object(module)
    db.init_app(app)

    # routes go here
    @app.route('/auth/register', methods=['GET', 'POST'])
    def register():
        """ return JSON response """
        if request.method == 'GET':
            return {
                'message': 'Welcome to the BucketList service',
                'more': 'Please make a POST /register \
                 with username and password'
            }, 200
        else:
            username = request.form.get('username')
            password = request.form.get('password')
            if username and password:
                return auth.register(username, password)
            else:
                raise ParseError()

    @app.route('/auth/login', methods=['GET', 'POST'])
    def login():
        """ login using a POST request, else prompt for credentials """
        if request.method == 'GET':
            raise CredentialsRequired()

        # handle POST login
        username = request.form.get('username')
        password = request.form.get('password')
        if auth.check_auth(username, password):
            return {
                'message': [
                    auth.SERVICE_MESSAGES['login'],
                    {
                        'available endpoint':
                        app.config.get('AVAILABLE_ENDPOINTS')
                    }
                ],
                'token': auth.generate_token(username, password)
            }
        else:
            raise AuthenticationFailed()

    @app.route('/auth/logout', methods=['GET'])
    def logout():
        """" Logs out a user """
        if auth.logout():
            return {'message': auth.SERVICE_MESSAGES['logout']}
        else:
            raise NotFound()

    @app.route('/bucketlists', methods=['POST', 'GET'])
    def bucketlist():
        """ Return a JSON response with all bucketlists """
        user_id = auth.get_current_user()
        results_data = None
        if request.method == 'GET':
            results = BucketList.query.filter_by(created_by=user_id)
            # pagination limit
            limit = request.args.get('limit', 20)
            q = request.args.get('q')
            page = request.args.get('page', 1)

            if results.all():
                if not 0 <= int(limit) <= 100:
                    raise NotAcceptable('Maximum limit per page is 100')
                else:
                    results_data = results
                if q:
                    results_data = results.filter(
                        BucketList.name.ilike('%{0}%'.format(q)))
                # serialize result objects to json
                result_list = []
                for item in results_data.paginate(
                        page, int(limit), False).items:
                    if callable(getattr(item, 'to_json')):
                        result = item.to_json()
                        result_list.append(result)
                results_data = result_list
                return {'message': results_data}

            raise NotFound('User has no bucketlist')

        else:
            name = request.form.get("name")
            bucketlist = BucketList(created_by=user_id, name=name)
            bucketlist.save()
            return {
                "message": "Bucketlist was created successfully",
                "bucketlist": bucketlist.to_json()}, 201

    @app.route('/bucketlists/<int:id>', methods=['GET', 'PUT', 'DELETE'])
    def edit_bucketlist(id, **kwargs):
        """ Edit a bucketlist:
            DELETE a bucketlist with its child items,
            UPDATE a bucketlist with its child items
        """
        bucketlist = BucketList.query.get(id)
        if request.method == 'DELETE':
            bucketlist.delete()
            return {"message": "Bucketlist was deleted successfully"}, 200

        elif request.method == 'PUT':
            name = request.form.get("name")
            bucketlist.name = name
            bucketlist.save()

        return bucketlist.to_json(), 200
    return app
