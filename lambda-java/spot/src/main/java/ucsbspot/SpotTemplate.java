package ucsbspot;

import java.util.*;
import java.lang.*;
import java.io.*;

import com.amazonaws.services.lambda.runtime.*;
import com.amazonaws.services.lambda.*;
import com.amazonaws.services.lambda.model.*;
import com.amazonaws.services.dynamodbv2.*;
import com.amazonaws.services.dynamodbv2.document.*;
import com.amazonaws.services.dynamodbv2.document.spec.*;
import com.amazonaws.services.dynamodbv2.document.utils.*;
import com.amazonaws.services.dynamodbv2.model.*;

import org.json.*;
import org.json.simple.JSONObject;
import org.json.simple.JSONArray;
import org.json.simple.parser.ParseException;
import org.json.simple.parser.JSONParser;

//without SpotWrap:
//public class SpotTemplate implements RequestStreamHandler 

//with SpotWrap:
public class SpotTemplate
{
    //not needed with SpotWrap: private JSONParser parser = new JSONParser();
    // enumeration of constants for various event types
    private static final short APIGW = 1; //API Gateway
    private static final short DYNDB = 2; //DynamoDB
    private static final short S3 = 3; //Simple Storage Service (S3)
    private static final short INVCLI = 4; //invoke via aws API (command line) external to or within a function

    ///////////////////  handler (entry point): handleRequest /////////////////
    //without SpotWrap:
    //public void handleRequest(InputStream inputStream, OutputStream outputStream, Context context) throws IOException 
    //with SpotWrap:
    public static JSONObject handleRequest(JSONObject event, Context context) 
    {
	/* generic handler for API manager, DynamoDB, and invoke events */

	long entry = System.currentTimeMillis();
        //context object details: https://gist.github.com/gene1wood/c0d37dfcb598fc133a8c
	//extract important information from context object
        LambdaLogger logger = context.getLogger();
	String thisReqID = context.getAwsRequestId();
	String thisFname = context.getFunctionName();
	String arn = context.getInvokedFunctionArn();

        JSONObject responseJson = new JSONObject();

	//not needed with SpotWrap:
        //BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream));
        long process_time = 0;
        long handler_time = 0;
	try{

	    //extract request object from inputStream
	    //without SpotWrap:
            //JSONObject req = (JSONObject)parser.parse(reader);
	    //with SpotWrap:
            JSONObject req = event;
            logger.log("event: " + req);

	    //do all of the work
	    long tmptime = System.currentTimeMillis();
            processEvent(thisReqID,thisFname,req,logger,responseJson,arn,entry);
	    process_time = System.currentTimeMillis()-tmptime;

        } catch(Exception e) {
            responseJson.put("statusCode", "400");
            responseJson.put("exception", e);
	    StringWriter sw = new StringWriter();
	    PrintWriter pw = new PrintWriter(sw);
	    e.printStackTrace(pw);
	    logger.log("stack trace: "+sw.toString());
        }

	//prepare response 
        JSONObject headerJson = new JSONObject();
        headerJson.put("x-custom-response-header", "Spot Template");
        responseJson.put("headers", headerJson);
        logger.log(responseJson.toJSONString());

	//without SpotWrap:
        //OutputStreamWriter writer = new OutputStreamWriter(outputStream, "UTF-8");
        //writer.write(responseJson.toJSONString());  //only returned if called synchronously (not if Event type)
        //writer.close();

	handler_time = System.currentTimeMillis()-entry;
	logger.log("TIMER:CALL:"+process_time+":HANDLER:"+handler_time);
        //with SpotWrap:
	return responseJson;
    }

    /////////////////////////  processEvent ///////////////////////////////
    //without SpotWrap:
    //private JSONObject processEvent(String thisReq, String fname, JSONObject event, LambdaLogger logger, JSONObject responseJson, String arn, long entry)
    //with SpotWrap:
    private static JSONObject processEvent(String thisReq, String fname, JSONObject event, LambdaLogger logger, JSONObject responseJson, String arn, long entry)
    {
	/* currently handled: API Gateway, S3, DynamoDB, and Invoke requests */

	/*setup response string defaults*/
	String eventSource = "unknown";
	String eventOp = "unknown";
	String caller = "unknown";
	String sourceIP = "000.000.000.000";
        String msg = "unset"; //random info
        String testCase = "unset"; //flag sent in (used only for INVCLI)
	String requestID = thisReq; //reqID of this aws lambda function
        String functionName = fname; //this aws lambda function name
	String[] arntok = arn.split(":");
	String region = arntok[3];
	String accountID = arntok[4];

	short flag = 0; //holds the type of event this is once we figure it out
        JSONObject responseBody = new JSONObject();

	/* Determine which type of request/event this is from the event JSON */
        Object test = event.get("requestContext");
	if (test != null) {
	    //API Gateway request
	    flag = APIGW;
	} else {
            test = event.get("Records"); //s3 and dynamoDB json have this JSONArray
	    if (test != null) {
		JSONObject testobj = (JSONObject)((JSONArray)test).get(0);
	 	if (testobj == null) {
		    flag = 0; //error unknown entry, expecting nonempty Records array
		} else {
		    //check eventSource for either aws:s3 or aws:dynamodb
		    String esObj = (String)testobj.get("eventSource");
		    if (esObj == null) {
		        flag = 0; //error unknown entry, expecting Record with eventSource key
		    } else {
			if (esObj.equals("aws:s3")) {
			    flag = S3;
			} else if (esObj.equals("aws:dynamodb")) {
			    flag = DYNDB;
			} else {
			    //default
		            flag = 0; //error unknown eventSource
	                    logger.log("processEvent: unknown Records/eventSource="+eventSource);
		        }
		    }
		}
	    } else { //no Records array (invoke or unknown event)
                test = event.get("eventSource");
	        if (test != null) {
		    if (((String)test).startsWith("ext:invokeCLI")){
	               //CLI Invoke
		       flag = INVCLI;
	 	    } else if (((String)test).startsWith("int:invokeCLI")){
	               //CLI Invoke
		       flag = INVCLI;
		    } else {
		        //default
		        flag = 0; //error unknown eventSource
	                logger.log("processEvent: unknown eventSource="+eventSource);
	 	    }
		} 
            }
	}

	/* setup json for response, logging, and DB recording -- for each event */
	try {
            if (flag == APIGW) { 
	        //unused: testCase
                JSONObject reqcontext = (JSONObject)event.get("requestContext");
                eventSource = "aws:APIGateway:"+(String)reqcontext.get("apiId");
                msg = (String)reqcontext.get("resourceId");
	        String actID = (String)reqcontext.get("accountId");
		if (!actID.equals(accountID)) {
		    accountID += ":"+actID;
	        }
	        caller = (String)reqcontext.get("requestId");
	        eventOp = (String)reqcontext.get("path");
	        JSONObject tmpJson = (JSONObject)reqcontext.get("identity");
	        if (tmpJson != null) {
	            sourceIP = (String)tmpJson.get("sourceIp");
	        }
                JSONObject qps = (JSONObject)event.get("queryStringParameters");
                if (qps != null) { 
                    if ( qps.get("msg") != null) {
                        msg += ":"+ (String)qps.get("msg");
                    }
                }
	    } else if (flag == INVCLI) { //unused sourceIP
		//eventSource will not be null at this point b/c we used it
		//to set flag
                eventSource = "aws:CLIInvoke:"+(String)event.get("eventSource");

                caller = (String)event.get("requestId");
		if (caller == null) {
		    caller = "unknown";
		}
	        msg = (String)event.get("msg");
		if (msg == null) {
		    msg = "unset";
	        }
	        String actID = (String)event.get("accountId");
		if (actID != null) {
		    if (!actID.equals(accountID)) {
		        accountID += ":"+actID;
	            }
                }
	        eventOp = (String)event.get("functionName");
		if (eventOp == null) { //use the eventSource instead
		    eventOp = (String)event.get("eventSource");
		    if (eventOp == null) {
		        eventOp = "unknown";
		    }
		}
	        testCase = (String)event.get("testCase");
		if (testCase == null) {
		    testCase = "unset";
		}

	    } else if (flag == DYNDB) { //unused sourceIP, testCase
                JSONArray recs = (JSONArray)event.get("Records");
		JSONObject obj = (JSONObject)recs.get(0);
	        eventSource = (String)obj.get("eventSource");
	        caller = (String)obj.get("eventID");
		String ev = (String)obj.get("eventName");

		/* all have SequenceNumber
		   options are MODIFY -> "NewImage":{"name":{"S":"zoe"},"age":{"N":"10"}}
		     -> OldImage{"name":{"S":"zoe"},"age":{"N":"10"}}
		   INSERT -> "NewImage":{"name":{"S":"zoe"},"age":{"N":"10"}}
		   REMOVE -> "OldImage":{"name":{"S":"from:dep_funcsB"},"age":{"N": "17"}}
		*/
		JSONObject ddbobj = (JSONObject)obj.get("dynamodb");
		String mod = "";
		if (ev.equals("MODIFY")) {
		    JSONObject ddbop = (JSONObject)ddbobj.get("NewImage");
		    mod = ddbop.toJSONString();
		    ddbop = (JSONObject)ddbobj.get("OldImage");
		    mod = mod+":"+ddbop.toJSONString();
		} else if (ev.equals("INSERT")) {
		    JSONObject ddbop = (JSONObject)ddbobj.get("NewImage");
		    mod = ddbop.toJSONString();
		} else if (ev.equals("REMOVE")) {
		    JSONObject ddbop = (JSONObject)ddbobj.get("OldImage");
		    mod = mod+":"+ddbop.toJSONString();
		}
		msg = ev+":"+(String)ddbobj.get("SequenceNumber")+":OP:"+mod;

		String arntmp = (String)obj.get("eventSourceARN");
		arntok = arntmp.split(":");
		String reg = arntok[3];
		if (!reg.equals(region)) {
		    region += ":"+reg;
	        }
		String actID = arntok[4];
		if (!actID.equals(accountID)) {
		    accountID += ":"+actID;
	        }
		String rest = "";
		for (int i = 5; i < arntok.length; i++){
		    rest += arntok[i];
		}
		eventOp = rest;
	    } else if (flag == S3) { //unused testCase
                JSONArray recs = (JSONArray)event.get("Records");
		JSONObject obj = (JSONObject)recs.get(0);
	        JSONObject s3obj = (JSONObject)obj.get("s3");
	        JSONObject s3bkt = (JSONObject)s3obj.get("bucket");
	        JSONObject s3bktobj = (JSONObject)s3obj.get("object");

	        JSONObject respobj = (JSONObject)obj.get("responseElements");
		if (respobj != null) {
	            caller = (String)respobj.get("x-amz-request-id");
		}
	        respobj = (JSONObject)obj.get("requestParameters");
		if (respobj != null) {
		    sourceIP = (String)respobj.get("sourceIPAddress");
		}
		respobj = (JSONObject)obj.get("userIdentity");
		if (respobj != null) {
	            String actID = (String)respobj.get("principalId");
		    if (!actID.equals(accountID)) {
		        accountID += ":"+actID;
	            }
		}
		if (obj != null && s3bkt != null && s3bktobj != null) {
		    String reg = (String)obj.get("awsRegion");
		    if (!reg.equals(region)) {
		        region += ":"+reg;
	            }
	    	    Object sz = s3bktobj.get("size");
		    String size = "0"; //size of 0 for delete
		    if (sz != null) {
		        size = ((Long)sz).toString();
		    }
			
		    eventOp = (String)obj.get("eventName");
	            eventSource = (String)obj.get("eventSource");
		    msg = (String)s3bkt.get("name") 
			+ ":" + (String)s3bktobj.get("key") 
			+ ":" + size
			+ ":" + (String)s3bktobj.get("sequencer") 
			+ ":" + (String)obj.get("eventTime");
		} else {
		    msg = "Error, unexpected JSON object and bucket";
	        }
            } else {
	        eventSource = "ERROR";
	    }
        }catch(Exception e){
	    logger.log("processEvent: exception="+e);
	    StringWriter sw = new StringWriter();
	    PrintWriter pw = new PrintWriter(sw);
	    e.printStackTrace(pw);
	    logger.log("stack trace: "+sw.toString());
	    flag = 0;
	}
    
        responseBody.put("requestID", requestID);
        responseBody.put("eventSource", eventSource);
        responseBody.put("eventOp", eventOp);
        responseBody.put("region", region);
        responseBody.put("caller", caller);
        responseBody.put("accountID", accountID);
        responseBody.put("sourceIP", sourceIP);
        responseBody.put("message", msg);
        responseBody.put("testCase", testCase);
        responseBody.put("functionName", functionName);
	logger.log("processEvent: reqID: "+thisReq+" responseBody="+responseBody.toString());

        //not needed with SpotWrap: log function in database (dynamodb table) if needed
	//get database handle - table must already exist
	//AmazonDynamoDB client = AmazonDynamoDBClientBuilder.standard().build();
	//DynamoDB dynamoDB = new DynamoDB(client);
	//Table table = dynamoDB.getTable("spotFunctionTable");
	//write to table (see Record.java)

	//prepare response for synchronous calls to invoke
	String body = responseBody.toString();
        responseJson.put("statusCode", "200");
        responseJson.put("body", body);
	logger.log("processEvent: returning: "+body);
	return responseJson;
    }
    
}
