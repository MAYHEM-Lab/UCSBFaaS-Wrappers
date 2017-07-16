package ucsbspot;  //Users: change this to match the package of your class

import java.io.*;
import org.json.simple.*;
import org.json.simple.parser.*;
import com.amazonaws.services.lambda.runtime.*;

public class SpotWrap implements RequestStreamHandler {
    private JSONParser parser = new JSONParser();

    ///////////////////  call user function  /////////////////
    private JSONObject callIt(JSONObject event, Context context){
	/* replace CLASSNAME.HANDLER in the statement below to your class and method to invoke.
	   The method must have the same signature as this method (callIt).
	   This SpotWrap class must have the same package name and be in the same directory
	   as your class.
         */
        //return CLASSNAME.HANDLER(event,context);
        return SpotTemplate.handleRequest(event,context);
    }

    ///////////////////////////////////////////////////////////////////////////////////
    ///////////////// Users: do not change anything in the code below /////////////////
    ///////////////////////////////////////////////////////////////////////////////////

    // enumeration of constants for various event types
    private static final short APIGW = 1; //API Gateway
    private static final short DYNDB = 2; //DynamoDB
    private static final short S3 = 3; //Simple Storage Service (S3)
    private static final short INVCLI = 4; //invoke via aws API (command line) external to or within a function
    ///////////////////  handler (entry point): handleRequest /////////////////
    public void handleRequest(InputStream inputStream, 
	OutputStream outputStream, Context context) throws IOException {
        LambdaLogger logger = context.getLogger();
        JSONObject userResp = new JSONObject();
        JSONObject event = null;
        long entry = 0;
        long exit = 0;
	boolean ERR = false;
	String errorstr = "SpotWrapJava"; //error msg: cannot be empty or null (dynamodb)
	try{
	    //extract request object from inputStream
            BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream));
            event = (JSONObject)parser.parse(reader);
	    Record.makeRecord(context,event,0L,errorstr); //start event (0L duration, and error=false)
	    entry = System.currentTimeMillis();
            userResp = callIt(event,context);

            String test = (String)userResp.get("statusCode");
	    if (test != null && !test.equals("200")) {
		ERR = true;
		errorstr = "error_unknown:status:" + test;
		Exception e = (Exception)userResp.get("exception");
		if (e != null) {
		    errorstr += e.toString() + ":status:" + test;
		}
	    }

        } catch (Exception e) {
	    ERR = true;
	    errorstr += ":SpotWrap_exception:"+e+":status:400";
	    StringWriter sw = new StringWriter();
	    PrintWriter pw = new PrintWriter(sw);
	    e.printStackTrace(pw);
	    logger.log("stack trace: "+e+"\n"+sw.toString());
	} finally {
	    long duration = System.currentTimeMillis() - entry;
	    if (entry == 0) {
		duration = 0;
            }
	    Record.makeRecord(context,null,duration,errorstr);//end event (event arg = null)
        }
	//prepare userResp for synchronous calls to invoke
	String status = "200";
	if (ERR) {
	    status = "400";
            userResp.put("SpotWrapError", errorstr);
        }
	String body = userResp.toString();
        JSONObject resp = new JSONObject();
        resp.put("statusCode", status);
        resp.put("body", body);
	logger.log("SpotWrapJava::handleRequest: returning: "+status+":"+body);
        OutputStreamWriter writer = new OutputStreamWriter(outputStream, "UTF-8");
        writer.write(resp.toJSONString());  //only returned if called synchronously
        writer.close();
    }
}
