from flask_restful import Resource, reqparse
import os
from flask import request, jsonify
from werkzeug.utils import secure_filename
from app.pkg.sui import SuiClient
from app.models.order import Order, db, OrderStatus

class AuditResource(Resource):
    def __init__(self, sui_client: SuiClient):
        self.sui_client = sui_client
        super(AuditResource, self).__init__()

    def post(self):
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

        return {
            'message': 'OK',
            'digest': digest,
            'saved_files': saved_files,
            'upload_directory': temp_dir
        }, 200

    def verify(self, digest: str, orderId: str):
        # 1. 根据 orderId 查询订单
        order = db.session.query(Order).filter_by(order_id=orderId).first()

        # 2. 检查订单是否存在
        if not order:
            print(f"Order with orderId {orderId} not found.")
            return False
        
        if order.status == OrderStatus.USED:
            print(f"Order {orderId} has already been used.")
            return False
        
        
        # 检查订单状态，如果已使用或已有摘要，则可能需要阻止重复处理？（根据业务逻辑决定）
        # if order.status == OrderStatus.USED or order.digest:
        #     print(f"Order {orderId} has already been processed or used.")
        #     return False

        # 3. 调用 Sui 客户端进行链上验证
        try:
            transactions = self.sui_client.query(digest)
            print("transactions: ", transactions)
            if not transactions or 'result' not in transactions:
                print(f"Sui query failed or returned unexpected structure for digest {digest}")
                return False
                
            if len(transactions['result']) == 0:
                print(f"No transaction found on Sui for digest {digest}")
                return False

            result = transactions['result'][0]
            event = result.get('parsedJson')
            packageId = result.get('packageId')

            if not event or not packageId:
                 print(f"Missing parsedJson or packageId in Sui transaction result for digest {digest}")
                 return False

            # ---- 在这里添加您的 Sui 交易验证逻辑 ----
            # 例如：检查 packageId, amount, event中的order_id等
            # 注意：下面的 packageId 和 amount 是示例值，请替换为您的实际值
            expected_package_id = "0x01122779d9e84092859fb998fa020a905e666dc273c42f0ba9766ec2eb7f1e3b"
            expected_amount = "100000"

            if packageId != expected_package_id:
                print(f"PackageId mismatch for digest {digest}. Expected {expected_package_id}, got {packageId}")
                return False

            if event.get('amount') != expected_amount:
                 print(f"Amount mismatch for digest {digest}. Expected {expected_amount}, got {event.get('amount')}")
                 return False

            order_id_array = event.get('order_id')
            if not order_id_array:
                 print(f"Missing order_id in event data for digest {digest}")
                 return False
                 
            order_id_string = ''.join(chr(num) for num in order_id_array)

            print("Decoded order_id from Sui event: ", order_id_string)

            if order_id_string != orderId:
                 print(f"OrderId mismatch. Expected from DB: {orderId}, got from Sui: {order_id_string}")
                 return False
            # ---- Sui 验证逻辑结束 ----


            # 4. 如果 Sui 验证通过，更新订单的 digest
            try:
                # 可以考虑同时更新状态，例如从未支付/待处理更新为已支付
                db.session.query(Order).filter_by(id=order.id).update({'digest': digest, 'status': OrderStatus.PAID})
                db.session.commit()
                print(f"Successfully verified and updated digest for order {orderId}")
                return True
            except Exception as e:
                db.session.rollback() # 如果更新失败，回滚事务
                print(f"Failed to update order {orderId} with digest {digest}: {e}")
                return False

        except Exception as e:
            print(f"Error during Sui client query or verification for digest {digest}: {e}")
            return False
        
