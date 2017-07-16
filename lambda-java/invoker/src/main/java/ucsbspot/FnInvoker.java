package ucsbspot;

import java.util.*;
import java.lang.*;
import java.io.*;
import org.json.simple.*;
import com.amazonaws.services.lambda.*;
import com.amazonaws.services.lambda.runtime.*;
import com.amazonaws.services.lambda.model.*;

public class FnInvoker {
    private final static String STOPMSG = "RECURSING";

    ///////////////////  handler (entry point): handleRequest /////////////////
    public static JSONObject handleRequest(JSONObject event, Context context) {

	/* This handler expects a JSONObject holding the event details, and a LambdaContext context.
	   event should hold:
	   "testCase":"any string"
	   "msg":"any string"
	   "functionName":"valid_aws_lamba_function_arn"
	   e.g. "functionName":"arn:arn:aws:lambda:us-west-2:443592014519:function:FnInvoker"
	   if "functionName" is invalid or not included, this function calls 
	   itself once asynchronously to test recursion, passing msg
	   If a valid arn is passed in for "functionName" key, this function invokes it.
	   handleRequest returns JSONObject response
	*/

	//extract important information from context object
        LambdaLogger logger = context.getLogger();
	String thisReqID = context.getAwsRequestId();
	String thisFname = context.getFunctionName();
	String arn = context.getInvokedFunctionArn();
	String[] arntok = arn.split(":");
	String region = arntok[3];
	String accountID = arntok[4];
        logger.log("FnInvoker: req:" + thisReqID+" fname:"+thisFname+" arn:"+arn+" acct:"+accountID);

        JSONObject responseJson = new JSONObject();
	try{
	    //initialization
            JSONObject req = event;
            logger.log("FnInvoker: " + req);
	    boolean recursive = false; //set up to recurse once
	    boolean skipInvoke = false; //if recursing or error, don't call invoke
	    String fnToCall = null; //the arn of the function to call

	    //parse request
	    String testCase = (String)req.get("testCase"); //ok if null, checked later
	    String msg = (String)req.get("msg");
	    if (msg == null) {
		msg = "";
	    }
            logger.log("INFO: msg passed in: "+msg);
	    String fname = (String)req.get("functionName");
	    if (fname == null) {
		fname = "";
	    }

	    long now = System.currentTimeMillis();
	    String nows = "callerts:"+Long.toString(now);
	    msg += ":"+nows; //add caller timestamp to msg
	    if (msg.indexOf(STOPMSG) != -1) {
		//we are in recursion, so stop
		skipInvoke = true;
                logger.log("INFO: skipping invocation, in recursive call: "+msg);
	    }
	    String val = (String)req.get("functionName");
	    if (val == null) {
	        //no valid function passed in, call this function recursively once
		fnToCall = arn;
		msg = STOPMSG+":1";
                logger.log("INFO: setting up to call myself recursively "+msg+" fn: "+arn);
	    } else if (val.equals(arn)) {
	        //A valid function was passed in but with this function's arn,
		//so we are in recursion. Do not continue invocation in this case.
		//This case also disallows anyone invoking this function directly
		//and sending in this function's arn (forcing recursion: is not allowed
		//to ensure safety of recursive execution)
		skipInvoke = true;
                logger.log("INFO: skipping invocation (function passed in has same arn)");
	    } else if (val.startsWith("arn:aws:lambda")) {//assume its OK and callit
		fnToCall = val;
	    }
	    if (fnToCall == null) skipInvoke = true; //safety check

	    //invoke the lambda function
	    if (!skipInvoke) {
                logger.log("INFO: implementing invocation msg: "+msg+" calling: "+fnToCall);
	        //setup function to call, 
	        JSONObject obj = new JSONObject();
	        //these are key/value pairs expected by SpotTemplate (else ignored)
	        obj.put("eventSource","int:invokeCLI"); //calling invoke
	        //record this function's (the caller's) info
	        obj.put("requestId",thisReqID); 
	        obj.put("accountId",accountID);
	        obj.put("functionName",arn); 
	        if (msg != null){
	            obj.put("msg",msg); 
	        }
	        if (testCase != null){
	            obj.put("testCase",testCase); 
	        }

                AWSLambdaAsync lam = AWSLambdaAsyncClientBuilder.defaultClient();
                InvokeRequest request = new InvokeRequest().withFunctionName(fnToCall).withPayload(obj.toString());
                InvokeResult invoke = lam.invoke(request);
                context.getLogger().log("invoke result: " + fnToCall + ": " + request + ": " +invoke.toString() +": "+ obj.toString());
	    }

            responseJson.put("statusCode", "200");

        } catch(Exception e) {
            responseJson.put("statusCode", "400");
            responseJson.put("exception", e);
	    StringWriter sw = new StringWriter();
	    PrintWriter pw = new PrintWriter(sw);
	    e.printStackTrace(pw);
	    logger.log("stack trace: "+sw.toString());
        }

	//prepare response 
	long now = System.currentTimeMillis();
        JSONObject headerJson = new JSONObject();
        headerJson.put("x-custom-response-header", "FnInvoker");
        responseJson.put("headers", headerJson);
        logger.log(responseJson.toJSONString());
	return responseJson;
    }
	
}
