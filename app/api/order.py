from flask_restful import Resource, reqparse
from app.models.order import Order, db
from app.pkg.sui import SuiClient
from flask import request

class OrderResource(Resource):
    def __init__(self, sui_client: SuiClient):
        self.sui_client = sui_client
        super(OrderResource, self).__init__()

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('status', type=str, required=False)
        args = parser.parse_args()
        
       
        try:
            new_order = Order()
            if args['status']:
                new_order.status = args['status']
            db.session.add(new_order)
            db.session.commit()
            
            return {
                'message': 'OK',
                'order': {
                    'id': new_order.id,
                    'order_id': new_order.order_id,
                    'status': new_order.status.value,
                    'created_at': new_order.created_at
                }
            }, 200
        except Exception as e:
            db.session.rollback()
            return {'message': f'ERR: {str(e)}'}, 500

    def get(self):
        digest = request.args.get('digest')
        if not digest:
            return {'message': 'digest参数不能为空'}, 400
            
        try:
            result = self.sui_client.query(digest)
            return {
                'message': 'OK',
                'order': result
            }, 200
        except Exception as e:
            return {'message': f'ERR: {str(e)}'}, 500
            