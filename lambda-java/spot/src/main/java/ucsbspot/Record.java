package ucsbspot;

import java.util.*;
import java.lang.*;
import java.io.*;
import org.json.simple.*;
import com.amazonaws.services.lambda.runtime.*;
import com.amazonaws.services.dynamodbv2.*;
import com.amazonaws.services.dynamodbv2.document.*;
import com.amazonaws.services.dynamodbv2.document.spec.*;
import com.amazonaws.services.dynamodbv2.document.utils.*;
import com.amazonaws.services.dynamodbv2.model.*;

public class Record {
    private final static String sessionID = UUID.randomUUID().toString();
    // enumeration of constants for various event types
    private static final short APIGW = 1; //API Gateway
    private static final short DYNDB = 2; //DynamoDB
    private static final short S3 = 3; //Simple Storage Service (S3)
    private static final short INVCLI = 4; //invoke via aws API (command line) external to or within a function

    public static void makeRecord(Context context, JSONObject event, 
        long duration, String errorstr) { //if event != null this is a start event, else its an end event
	/* currently handled: API Gateway, S3, DynamoDB, and Invoke requests */

	/*setup record defaults*/
	String eventSource = "unknown";
	String eventOp = "unknown";
	String caller = "unknown";
	String sourceIP = "000.000.000.000";
        String msg = "unset"; //random info
	String requestID = sessionID; //reqID of this aws lambda function; set random as default
        String functionName = "unset"; //this aws lambda function name
	String arn = "unset";
	String region = "unset";
	String accountID = "unset";
	short flag = 0; //holds the type of event this is once we figure it out
        LambdaLogger logger = null;
	String[] arntok = null;

        if (context != null) {
            //context object details: https://gist.github.com/gene1wood/c0d37dfcb598fc133a8c
            logger = context.getLogger();

	    requestID = context.getAwsRequestId(); //reqID of this aws lambda function
            functionName = context.getFunctionName(); //this aws lambda function name
	    arn = context.getInvokedFunctionArn();
	    arntok = arn.split(":");
	    region = arntok[3];
	    accountID = arntok[4];
        } //context null check

        if (event != null) {
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
		                if (logger != null) {
	                            logger.log("SpotWrap::makeRecord: unknown Records/eventSource="+esObj);
				}
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
		            if (logger != null) {
	                        logger.log("SpotWrap::makeRecord: unknown eventSource="+((String)test));
		            }
	 	        }
		    } 
                }
	    }
    
	    /* extract details from json event for DB recording according to flag/trigger type */
	    try {
                if (flag == APIGW) { 
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
    
	        } else if (flag == DYNDB) { //unused sourceIP
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
	        } else if (flag == S3) { 
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
	            eventSource = "unknown_source:"+functionName;
	        }
            }catch(Exception e){
	        StringWriter sw = new StringWriter();
	        PrintWriter pw = new PrintWriter(sw);
	        e.printStackTrace(pw);
		if (logger != null) {
	            logger.log("SpotWrap: Error processing event: "+e);
	            logger.log("stack trace: "+sw.toString());
		}
	        flag = 0;
	    }
        
        } //event null check

	if (eventSource.equals("unset")) {
	    //if functionName is "unset" then context is null!
	    eventSource = "unknown_source:"+functionName;
	}
	/* write lambda invocation record to dynamoDB */
	//get database handle - table must already exist
	AmazonDynamoDB client = AmazonDynamoDBClientBuilder.standard().build();
	DynamoDB dynamoDB = new DynamoDB(client);
	Table table = dynamoDB.getTable("spotFnTable");
	long now = System.currentTimeMillis();
	Item item = new Item().withPrimaryKey("requestID", requestID)
    	        .withNumber("ts", now)
    	        .withString("thisFnARN", arn)
    	        .withString("caller", caller)
    	        .withString("eventSource", eventSource)
    	        .withString("eventOp", eventOp)
    	        .withString("region", region)
    	        .withString("accountID",accountID)
    	        .withString("sourceIP",sourceIP)
    	        .withString("message",msg)
    	        .withNumber("duration", duration)
    	        .withString("start", String.valueOf(event != null))
    	        .withString("error", errorstr);
        PutItemOutcome outcome = table.putItem(item);
    }
}
