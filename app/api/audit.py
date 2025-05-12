from flask_restful import Resource, reqparse
import os
from flask import request, current_app
from werkzeug.utils import secure_filename
from app.pkg.sui.sui import SuiClient
from app.models.order import Order, db, OrderStatus
from app.pkg.agents.manager import ClientManager
from app.pkg.agents.audit import AuditStatus
class AuditResource(Resource):
    def __init__(self, sui_client: SuiClient, client_manager: ClientManager):
        self.sui_client = sui_client
        self.client_manager = client_manager
        super(AuditResource, self).__init__()

    def post(self):
        logger = current_app.logger
        if 'digest' not in request.form:
            return {'message': 'No digest part in the request'}, 400
        if 'files' not in request.files:
            return {'message': 'No file part in the request'}, 400
        if 'orderId' not in request.form:
            return {'message': 'No orderId part in the request'}, 400

        orderId = request.form['orderId']
        digest = request.form['digest']
        files = request.files.getlist('files')
        
        if not digest:
             return {'message': 'Digest cannot be empty'}, 400
        if not files or all(f.filename == '' for f in files):
             return {'message': 'No selected files'}, 400

    
        temp_dir = os.path.join('tmp', digest)
        try:
            os.makedirs(temp_dir, exist_ok=True)
        except OSError as e:
             print("create directory error: ", e)
             return {'message': f'Server error'}, 500

        
        try:
            if not self.verify(digest, orderId):
                return {'message': 'Verify error'}, 500
        except Exception as e:
            print("verify error: ", e)
            return {'message': f'Verify error'}, 500
        
        logger.debug("audit orderId: %s, digest: %s", orderId, digest)
        
        saved_files = []
    
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                
                if not filename.lower().endswith('.move'):
                    return {'message': f'Invalid file type: {filename}. Only .move files are allowed.'}, 400
                file_path = os.path.join(temp_dir, filename)
                try:
                    file.save(file_path)
                    saved_files.append(filename)
                except Exception as e:
                    return {'message': f'Failed to save file {filename}: {e}'}, 500
                


        try:
            logger.debug("create client orderId%s, temp_dir %s ======", orderId, temp_dir)
            self.client_manager.create(orderId, temp_dir)
            result = db.session.query(Order).filter_by(order_id=orderId).update({'status': OrderStatus.USED})
            logger.debug("Update order %s  result: %d", orderId, result)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to create client for orderId: {orderId}, error: {str(e)}", exc_info=True)
            return {'message': f'Create client error'}, 500

        return {
            'message': 'OK',
            'digest': digest,
            'saved_files': saved_files,
            'upload_directory': temp_dir
        }, 200

    def verify(self, digest: str, orderId: str):
        logger = current_app.logger
        order = db.session.query(Order).filter_by(order_id=orderId).first()

        if not order:
            logger.error(f"Order with orderId {orderId} not found.")
            return False
        
        if order.status == OrderStatus.USED:
            logger.error(f"Order {orderId} has already been used.")
            return False
    
        try:
            transactions = self.sui_client.query(digest)
            logger.debug("transactions: %s", str(transactions))
            if not transactions or 'result' not in transactions:
                logger.error(f"Sui query failed or returned unexpected structure for digest {digest}")
                return False
                
            if len(transactions['result']) == 0:
                logger.error(f"No transaction found on Sui for digest {digest}")
                return False

            result = transactions['result'][0]
            event = result.get('parsedJson')
            packageId = result.get('packageId')

            if not event or not packageId:
                logger.error(f"Missing parsedJson or packageId in Sui transaction result for digest {digest}")
                return False

            expected_package_id = "0x01122779d9e84092859fb998fa020a905e666dc273c42f0ba9766ec2eb7f1e3b"
            expected_amount = "100000"

            if packageId != expected_package_id:
                logger.error(f"PackageId mismatch for digest {digest}. Expected {expected_package_id}, got {packageId}")
                return False

            if event.get('amount') != expected_amount:
                logger.error(f"Amount mismatch for digest {digest}. Expected {expected_amount}, got {event.get('amount')}")
                return False

            order_id_array = event.get('order_id')
            if not order_id_array:
                logger.error(f"Missing order_id in event data for digest {digest}")
                return False
                 
            order_id_string = ''.join(chr(num) for num in order_id_array)

            logger.debug("Decoded order_id from Sui event: %s", order_id_string)

            if order_id_string != orderId:
                logger.error(f"OrderId mismatch. Expected from DB: {orderId}, got from Sui: {order_id_string}")
                return False

            try:
                db.session.query(Order).filter_by(id=order.id).update({'digest': digest, 'status': OrderStatus.PAID})
                db.session.commit()
                logger.debug(f"Successfully verified and updated digest for order {orderId}")
                return True
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to update order {orderId} with digest {digest}: {e}")
                return False

        except Exception as e:
            logger.error(f"Error during Sui client query or verification for digest {digest}: {e}", exc_info=True)
            return False
        
    
    def get(self):
        logger = current_app.logger
        orderId = request.args.get('orderId')
        if not orderId:
            return {'message': 'orderId can not be null'}, 400
        
        order = db.session.query(Order).filter_by(order_id=orderId).first()
        if not order:
            return {'message': 'order not exist'}, 400
        
        if order.status == OrderStatus.PENDING:
            return {'message': 'order not paid'}, 400
        
        blodId = ""
        directory = ""
        status = ""

        if order.status == OrderStatus.USED and order.blob_id != "":
            blodId = order.blob_id
            directory = os.path.join('tmp', order.digest, "report.pdf")
            status = AuditStatus.Reported.value
        else:
            client = self.client_manager.get(orderId)
            if not client:
                logger.error(f"Client not found for orderId: {orderId}")
                return {'message': 'client not exist'}, 400
            blodId = client.getBlobId()
            directory = client.getDirectory()
            status = client.getStatus()

        return {'message': 'OK', 'status': status, 'blodId': blodId, "directory": directory}, 200
        
        