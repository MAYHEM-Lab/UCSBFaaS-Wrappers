// Copyright 2012-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
// Licensed under the Apache License, Version 2.0.
package com.amazon.codesamples;

import java.lang.Thread;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.amazonaws.AmazonClientException;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDB;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDBClientBuilder;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDBStreams;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDBStreamsClientBuilder;
import com.amazonaws.services.dynamodbv2.model.AttributeAction;
import com.amazonaws.services.dynamodbv2.model.AttributeDefinition;
import com.amazonaws.services.dynamodbv2.model.AttributeValue;
import com.amazonaws.services.dynamodbv2.model.AttributeValueUpdate;
import com.amazonaws.services.dynamodbv2.model.CreateTableRequest;
import com.amazonaws.services.dynamodbv2.model.StreamDescription;
import com.amazonaws.services.dynamodbv2.model.DescribeStreamRequest;
import com.amazonaws.services.dynamodbv2.model.DescribeStreamResult;
import com.amazonaws.services.dynamodbv2.model.DescribeTableResult;
import com.amazonaws.services.dynamodbv2.model.GetRecordsRequest;
import com.amazonaws.services.dynamodbv2.model.GetRecordsResult;
import com.amazonaws.services.dynamodbv2.model.GetShardIteratorRequest;
import com.amazonaws.services.dynamodbv2.model.GetShardIteratorResult;
import com.amazonaws.services.dynamodbv2.model.KeySchemaElement;
import com.amazonaws.services.dynamodbv2.model.KeyType;
import com.amazonaws.services.dynamodbv2.model.ProvisionedThroughput;
import com.amazonaws.services.dynamodbv2.model.Record;
import com.amazonaws.services.dynamodbv2.model.Shard;
import com.amazonaws.services.dynamodbv2.model.ShardIteratorType;
import com.amazonaws.services.dynamodbv2.model.StreamSpecification;
import com.amazonaws.services.dynamodbv2.model.StreamViewType;
import com.amazonaws.services.dynamodbv2.util.TableUtils;

public class GetStreamData {
          
    public static void main(String args[]) throws InterruptedException {

	AmazonDynamoDB dynamoDBClient = AmazonDynamoDBClientBuilder.standard().build();
	AmazonDynamoDBStreams streamsClient = AmazonDynamoDBStreamsClientBuilder.standard().build();
	 
        // Create the table
        String tableName = "spotFns";
        // Determine the Streams settings for the table
        DescribeTableResult describeTableResult = dynamoDBClient.describeTable(tableName);
        String myStreamArn = describeTableResult.getTable().getLatestStreamArn();
        System.out.println("Current stream ARN for " + tableName + ": " + myStreamArn);

        // Setup up to get shards from stream
        DescribeStreamRequest describeStreamRequest = new DescribeStreamRequest();
        describeStreamRequest.setStreamArn( myStreamArn );
        List<Shard> shards = new ArrayList<>();
        String exclusiveStartShardId = null;

        // Process each shard
        do {
            describeStreamRequest.setExclusiveStartShardId( exclusiveStartShardId );
            DescribeStreamResult describeStreamResult = streamsClient.describeStream( describeStreamRequest );
            shards.addAll( describeStreamResult.getStreamDescription().getShards() );
            StreamDescription streamDescription = describeStreamResult.getStreamDescription();

            if (shards.size() > 0) {
                exclusiveStartShardId = streamDescription.getLastEvaluatedShardId();
            } else {
                exclusiveStartShardId = null;
            }
            System.out.println("startid: "+exclusiveStartShardId);

            for (Shard shard : shards) {
                String shardId = shard.getShardId();
                String start = shard.getSequenceNumberRange().getStartingSequenceNumber();
                String end = shard.getSequenceNumberRange().getEndingSequenceNumber();
                System.out.println("SHARD " + shardId + " parent " + shard.getParentShardId());
                System.out.println("start " + start + " end " + end);

                // Get an iterator for the current shard
                GetShardIteratorRequest getShardIteratorRequest = new GetShardIteratorRequest()
                    .withStreamArn(myStreamArn)
                    .withShardId(shardId)
                    .withShardIteratorType(ShardIteratorType.TRIM_HORIZON);
                GetShardIteratorResult getShardIteratorResult = 
                    streamsClient.getShardIterator(getShardIteratorRequest);

                String nextItr = getShardIteratorResult.getShardIterator();
                int count = 0;
                //open ended stream when end==null so make 10 tries (records.size() == 0) before breaking out of loop
                int MAXCOUNT = 10;
                while (nextItr != null && count < MAXCOUNT) {
                    // Use the iterator to read the data records from the shard
                    GetRecordsResult getRecordsResult = streamsClient
                        .getRecords(new GetRecordsRequest().withShardIterator(nextItr));
                    List<Record> records = getRecordsResult.getRecords();
    
                    int len = records.size();
                    System.out.println(len +" Records");
                    for (Record record : records) {
                        System.out.println(record);
                    }
                    nextItr = getRecordsResult.getNextShardIterator();
                    if (nextItr == null) {
                        System.out.println("END_OF_SHARD_ITERATOR");
                    }
                    count++;
                }
            }
            Thread.sleep(1000);
        } while ( exclusiveStartShardId != null );
    }
}



