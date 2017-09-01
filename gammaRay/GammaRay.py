#DO NOT CHANGE this file (setupApps depends on them)
import boto3,json,logging,os,sys,importlib,zipfile,traceback
import time,uuid
from fleece.xray import (monkey_patch_botocore_for_xray,
                         monkey_patch_requests_for_xray,
                         trace_xray_subsegment)

monkey_patch_botocore_for_xray()
monkey_patch_requests_for_xray()
sessionID = str(uuid.uuid4())

def callIt(event,context):
    #DO NOT CHANGE the following two lines (setupApps depends on them)
    #create a new file if changes are necessary
    import GammaRayTemplate
    return GammaRayTemplate.handler(event,context)

def handleRequest(event, context):
    logger = logging.getLogger()
    reqID = 'unknown'
    arn = 'unknown'
    if context:
        reqID = context.aws_request_id
        arn = context.invoked_function_arn
    os.environ['spotReqID'] = reqID
    os.environ['myArn'] = arn
    os.environ['gammaTable'] = 'QQQQ'
    os.environ['gammaRegion'] = 'ZZZZ'
    errorstr = "GammaWrapPython"
    logger.warn('GammaWrapPython::reqID:{}'.format(reqID))
    respObj = {}
    returnObj = {}
    status = '200'
    delta = 0
    wrappedentry = time.time() * 1000
    ERR = False
    try: 
        respObj = callIt(event,context)
        if not respObj:
            respObj = {}
            respObj['GammaWrapMessage'] = 'NoResponseReturned'
        if 'statusCode' in respObj:
            status = respObj['statusCode']
            if status != '200':
                ERR = True
                if 'exception' in respObj:
                    errorstr += ':{}:status:{}'.format(respObj['exception'],errcode)
                else:
                    errorstr += ':error_unknown:status:{}'.format(errcode)
    except Exception as e:
        _, _, exc_traceback = sys.exc_info()
        msg = repr(traceback.format_tb(exc_traceback))
        errorstr += ':GammaWrap_exception:{}:{}:status:400'.format(e,msg)
        ERR = True
    finally: 
        if errorstr != 'GammaWrapPython':
            print('GammaWrapPy caught error: {}'.format(errorstr))
        delta = (time.time() * 1000) - wrappedentry

    if not respObj: 
        respObj = {}
    if ERR:
        status = '400'
        respObj['GammaWrapError']=errorstr
    returnObj['statusCode'] = status
    returnObj['body'] = respObj
    selfdelta = (time.time() * 1000) - entry
    logger.warn('GammaWrapPython::handleRequest:TIMER:CALL:{}:WRAPPEDCALL:{}:status:{}:response:{}'.format(selfdelta,delta,status,respObj))
    return returnObj
    
