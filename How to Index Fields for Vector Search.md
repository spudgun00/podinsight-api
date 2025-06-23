How to Index Fields for Vector Search


You can use the vectorSearch type to index fields for running $vectorSearch queries. You can define the index for the vector embeddings that you want to query and any additional fields that you want to use to pre-filter your data. Filtering your data is useful to narrow the scope of your semantic search and ensure that certain vector embeddings are not considered for comparison, such as in a multi-tenant environment.

You can use the Atlas UI, Atlas Administration API, Atlas CLI, mongosh, or a supported MongoDB Driver to create your Atlas Vector Search index.

Note
You can't use the deprecated knnBeta operator to query fields indexed using the vectorSearch type index definition.

Considerations
In a vectorSearch type index definition, you can index arrays with only a single element. You can't index fields inside arrays of documents or fields inside arrays of objects. You can index fields inside documents using the dot notation.

Before indexing your embeddings, we recommend converting your embeddings to BSON BinData vectors with subtype float32, int1, or int8 for efficient storage in your Atlas cluster. To learn more, see how to convert your embeddings to BSON vectors.

When you use Atlas Vector Search indexes, you might experience elevated resource consumption on an idle node for your Atlas cluster. This is due to the underlying mongot process, which performs various essential operations for Atlas Vector Search. The CPU utilization on an idle node can vary depending on the number, complexity, and size of the indexes.

To learn more about sizing considerations for your indexes, see Memory Requirements for Indexing Vectors.

Supported Clients
You can create and manage Atlas Vector Search indexes through the Atlas UI, mongosh, Atlas CLI, Atlas Administration API, and the following MongoDB Drivers:

MongoDB Driver
Version
C

1.28.0 or higher

C++

3.11.0 or higher

C#

3.1.0 or higher

Go

1.16.0 or higher

Java

5.2.0 or higher

Kotlin

5.2.0 or higher

Node

6.6.0 or higher

PHP

1.20.0 or higher

Python

4.7 or higher

Rust

3.1.0 or higher

Scala

5.2.0 or higher

Syntax
The following syntax defines the vectorSearch index type:

{
  "fields":[
    {
      "type": "vector",
      "path": "<field-to-index>",
      "numDimensions": <number-of-dimensions>,
      "similarity": "euclidean | cosine | dotProduct",
      "quantization": "none | scalar | binary",
      "hnswOptions": {
        "maxEdges": <number-of-connected-neighbors>,
        "numEdgeCandidates": <number-of-nearest-neighbors>
      }
    },
    {
      "type": "filter",
      "path": "<field-to-index>"
    },
    ...
  ]
}

Atlas Vector Search Index Fields
The Atlas Vector Search index definition takes the following fields:

Option
Type
Necessity
Purpose
fields

Array of field definition documents

Required

Definitions for the vector and filter fields to index, one definition per document. Each field definition document specifies the type, path, and other configuration options for the field to index.

The fields array must contain at least one vector-type field definition. You can add additional filter-type field definitions to your array to pre-filter your data.

fields.type

String

Required

Field type to use to index fields for $vectorSearch. You can specify one of the following values:

vector - for fields that contain vector embeddings.

filter - for additional fields to filter on. You can filter on boolean, date, objectId, numeric, string, and UUID values, including arrays of these types.

To learn more, see About the vector Type and About the filter Type.

fields.path

String

Required

Name of the field to index. For nested fields, use dot notation to specify path to embedded fields.

fields.numDimensions

Int

Required

Number of vector dimensions that Atlas Vector Search enforces at index-time and query-time. You can set this field only for vector-type fields. You must specify a value less than or equal to 8192.

For indexing quantized vectors or BinData, you can specify one of the following values:

1 to 8192 for int8 vectors for ingestion.

Multiple of 8 for int1 vectors for ingestion.

1 to 8192 for binData(float32) and array(float32) vectors for automatic scalar quantization.

Multiple of 8 for binData(float32) and array(float32) vectors for automatic binary quantization.

The embedding model you choose determines the number of dimensions in your vector embeddings, with some models having multiple options for how many dimensions are output. To learn more, see Choosing a Method to Create Embeddings.

fields.similarity

String

Required

Vector similarity function to use to search for top K-nearest neighbors. You can set this field only for vector-type fields.

You can specify one of the following values:

euclidean - measures the distance between ends of vectors.

cosine - measures similarity based on the angle between vectors.

dotProduct - measures similarity like cosine, but takes into account the magnitude of the vector.

To learn more, see About the Similarity Functions.

fields.quantization

String

Optional

Type of automatic vector quantization for your vectors. Use this setting only if your embeddings are float or double vectors.

You can specify one of the following values:

none - Indicates no automatic quantization for the vector embeddings. Use this setting if you have pre-quantized vectors for ingestion. If omitted, this is the default value.

scalar - Indicates scalar quantization, which transforms values to 1 byte integers.

binary - Indicates binary quantization, which transforms values to a single bit. To use this value, numDimensions must be a multiple of 8.

If precision is critical, select none or scalar instead of binary.

To learn more, see Vector Quantization.

fields.hnswOptions

Object

Optional

Parameters to use for Hierarchical Navigable Small Worlds graph construction. If omitted, uses the default values for the maxEdges and numEdgeCandidates parameters.

Important
This is available as a Preview feature. Modifying the default values might negatively impact your Atlas Vector Search index and queries.

fields.hnswOptions.maxEdges

Int

Optional

Maximum number of edges (or connections) that a node can have in the Hierarchical Navigable Small Worlds graph. Value can be between 16 and 64, both inclusive. If omitted, defaults to 16. For example, for a value of 16, each node can have a maximum of sixteen outgoing edges at each layer of the Hierarchical Navigable Small Worlds graph.

A higher number improves recall (accuracy of search results) because the graph is better connected. However, this slows down query speed because of the number of neighbors to evaluate per graph node, increases the memory for the Hierarchical Navigable Small Worlds graph because each node stores more connections, and slows down indexing because Atlas Vector Search evaluates more neighbors and adjusts for every new node added to the graph.

fields.hnswOptions.numEdgeCandidates

Int

Optional

Analogous to numCandidates at query-time, this parameter controls the maximum number of nodes to evaluate to find the closest neighbors to connect to a new node. Value can be between 100 and 3200, both inclusive. If omitted, defaults to 100.

A higher number provides a graph with high-quality connections, which can improve search quality (recall), but it can also negatively affect query latency.

About the vector Type
Your index definition's vector field must contain an array of numbers of one of the following types:

BSON double

BSON BinData vector subtype float32

BSON BinData vector subtype int1

BSON BinData vector subtype int8

Note
To learn more about generating BSON BinData vectors with subtype float32 int1 or int8 for your data, see How to Ingest Pre-Quantized Vectors.

You must index the vector field as the vector type inside the fields array.

The following syntax defines the vector field type:

{
  "fields":[
    {
      "type": "vector",
      "path": <field-to-index>,
      "numDimensions": <number-of-dimensions>,
      "similarity": "euclidean | cosine | dotProduct",
      "quantization": "none | scalar | binary",
      "hnswOptions": {
        "maxEdges": <number-of-connected-neighbors>,
        "numEdgeCandidates": <number-of-nearest-neighbors>
      }
    },
    ...
  ]
}

About the Similarity Functions
Atlas Vector Search supports the following similarity functions:

euclidean - measures the distance between ends of vectors. This value allows you to measure similarity based on varying dimensions. To learn more, see Euclidean.

cosine - measures similarity based on the angle between vectors. This value allows you to measure similarity that isn't scaled by magnitude. You can't use zero magnitude vectors with cosine. To measure cosine similarity, we recommend that you normalize your vectors and use dotProduct instead.

dotProduct - measures similarity like cosine, but takes into account the magnitude of the vector. If you normalize the magnitude, cosine and dotProduct are almost identical in measuring similarity.

To use dotProduct, you must normalize the vector to unit length at index-time and query-time.

The following table shows the similarity functions for the various types:

Vector Embeddings Type
euclidean
cosine
dotProduct
binData(int1) 

√

binData(int8) 

√

√

√

binData(float32) 

√

√

√

array(float32) 

√

√

√

 For vector ingestion.

 For automatic scalar or binary quantization.

For best performance, check your embedding model to determine which similarity function aligns with your embedding model's training process. If you don't have any guidance, start with dotProduct. Setting fields.similarity to the dotProduct value allows you to efficiently measure similarity based on both angle and magnitude. dotProduct consumes less computational resources than cosine and is efficient when vectors are of unit length. However, if your vectors aren't normalized, evaluate the similarity scores in the results of a sample query for euclidean distance and cosine similarity to determine which corresponds to reasonable results.

About the filter Type
You can optionally index additional fields to pre-filter your data. You can filter on boolean, date, objectId, numeric, string, and UUID values, including arrays of these types. Filtering your data is useful to narrow the scope of your semantic search and ensure that not all vectors are considered for comparison. It reduces the number of documents against which to run similarity comparisons, which can decrease query latency and increase the accuracy of search results.

You must index the fields that you want to filter by using the filter type inside the fields array.

The following syntax defines the filter field type:

{
  "fields":[
    {
      "type": "vector",
      ...
    },
    {
      "type": "filter",
      "path": "<field-to-index>"
    },
    ...
  ]
}

Note
Pre-filtering your data doesn't affect the score that Atlas Vector Search returns using $vectorSearchScore for $vectorSearch queries.

Create an Atlas Vector Search Index
You can create an Atlas Vector Search index for all collections that contain vector embeddings less than or equal to 8192 dimensions in length for any kind of data along with other data on your Atlas cluster through the Atlas UI, Atlas Administration API, Atlas CLI, mongosh, or a supported MongoDB Driver.

Prerequisites
To create an Atlas Vector Search index, you must have an Atlas cluster with the following prerequisites:

MongoDB version 6.0.11, 7.0.2, or higher

A collection for which to create the Atlas Vector Search index

Note
You can use the mongosh command or driver helper methods to create Atlas Vector Search indexes on all Atlas cluster tiers. For a list of supported driver versions, see Supported Clients.

Required Access
You need the Project Data Access Admin or higher role to create and manage Atlas Vector Search indexes.

Index Limitations
You cannot create more than:

3 indexes (regardless of the type, search or vector) on M0 clusters.

10 indexes on Flex clusters.

We recommend that you create no more than 2,500 search indexes on a single M10+ cluster.

Procedure
➤ Use the Select your language drop-down menu to select the client you want to use to create your index.

Note
The procedure includes index definition examples for the embedded_movies collection in the sample_mflix database. If you load the sample data on your cluster and create the example Atlas Vector Search indexes for this collection, you can run the sample $vectorSearch queries against this collection. To learn more about the sample queries that you can run, see $vectorSearch Examples.

To create an Atlas Vector Search index for a collection using the Atlas Administration API, send a POST request to the Atlas Search indexes endpoint with the required parameters.

curl --user "{PUBLIC-KEY}:{PRIVATE-KEY}" --digest \
--header "Accept: application/json" \
--header "Content-Type: application/json" \
--include \
--request POST "https://cloud.mongodb.com/api/atlas/v2/groups/{groupId}/clusters/{clusterName}/search/indexes" \
--data '
  {
    "database": "<name-of-database>",
    "collectionName": "<name-of-collection>",
    "type": "vectorSearch",
    "name": "<index-name>",
    "definition": {
      "fields":[ 
        {
          "type": "vector",
          "path": <field-to-index>,
          "numDimensions": <number-of-dimensions>,
          "similarity": "euclidean | cosine | dotProduct"
        },
        {
          "type": "filter",
          "path": "<field-to-index>"
        },
        ...
      }
    ]
  }'

To learn more about the syntax and parameters for the endpoint, see Create One Atlas Search Index.

Example
The following index definition indexes the plot_embedding field as the vector type. The plot_embedding field contains embeddings created using OpenAI's text-embedding-ada-002 embeddings model. The index definition specifies 1536 vector dimensions and measures similarity using dotProduct function.


Basic Example

Filter Example
The following index definition indexes only the vector embeddings field for performing vector search.

curl --user "{PUBLIC-KEY}:{PRIVATE-KEY}" --digest \
--header "Accept: application/json" \
--header "Content-Type: application/json" \
--include \
--request POST "https://cloud.mongodb.com/api/atlas/v2/groups/{groupId}/clusters/{clusterName}/search/indexes" \
--data '
  {
    "database": "sample_mflix",
    "collectionName": "embedded_movies",
    "type": "vectorSearch",
    "name": "vector_index",
    "definition: {
      "fields":[ 
        {
          "type": "vector",
          "path": "plot_embedding",
          "numDimensions": 1536,
          "similarity": "dotProduct"
        }
      ]
    }
  }'

View an Atlas Vector Search Index
You can view Atlas Vector Search indexes for all collections from the Atlas UI, Atlas Administration API, Atlas CLI, mongosh, or a supported MongoDB Driver.

Required Access
You need the Project Search Index Editor or higher role to view Atlas Vector Search indexes.

Note
You can use the mongosh command or driver helper methods to retrieve Atlas Vector Search indexes on all Atlas cluster tiers. For a list of supported driver versions, see Supported Clients.

Procedure
➤ Use the Select your language drop-down menu to set the language of the example in this section.

To retrieve all the Atlas Vector Search indexes for a collection using the Atlas Administration API, send a GET request to the Atlas Search indexes endpoint with the name of the database and collection.

curl --user "{PUBLIC-KEY}:{PRIVATE-KEY}" --digest \
     --header "Accept: application/json" \
     --include \
     --request GET "https://cloud.mongodb.com/api/atlas/v2/groups/{groupId}/clusters/{clusterName}/search/indexes/{databaseName}/{collectionName}"

To learn more about the syntax and parameters for the endpoint, see Return All Atlas Search Indexes for One Collection.

To retrieve one Atlas Vector Search index for a collection using the Atlas Administration API, send a GET request to the Atlas Search indexes endpoint with either the unique ID or name of the index (line 4) to retrieve.

curl --user "{PUBLIC-KEY}:{PRIVATE-KEY}" --digest \
     --header "Accept: application/json" \
     --include \
     --request GET "https://cloud.mongodb.com/api/atlas/v2/groups/{groupId}/clusters/{clusterName}/search/indexes/{indexId} | https://cloud.mongodb.com/api/atlas/v2/groups/{groupId}/clusters/{clusterName}/search/indexes/{databaseName}/{collectionName}/{indexName|indexId}"

To learn more about the syntax and parameters for the endpoint, Get One By Name and Get One By ID.

Edit an Atlas Vector Search Index
You can change the index definition of an existing Atlas Vector Search index from the Atlas UI, Atlas Administration API, Atlas CLI, mongosh, or a supported MongoDB Driver. You can't rename an index or change the index type. If you need to change an index name or type, you must create a new index and delete the old one.

Important
After you edit an index, Atlas Vector Search rebuilds it. While the index rebuilds, you can continue to run vector search queries by using the old index definition. When the index finishes rebuilding, the old index is automatically replaced. This process is similar to Atlas Search indexes. To learn more, see Creating and Updating an Atlas Search Index.

Required Access
You must have the Project Search Index Editor or higher role to edit an Atlas Vector Search index.

Note
You can use the mongosh command or driver helper methods to edit Atlas Vector Search indexes on all Atlas cluster tiers. For a list of supported driver versions, see Supported Clients.

Procedure
➤ Use the Select your language drop-down menu to select the client you want to use to edit your index.

To edit an Atlas Vector Search index for a collection using the Atlas Administration API, send a PATCH request to the Atlas Search indexes endpoint with either the unique ID or name of the index (line 4) to edit.

curl --user "{PUBLIC-KEY}:{PRIVATE-KEY}" --digest --include \
     --header "Accept: application/json" \
     --header "Content-Type: application/json" \
     --request PATCH "https://cloud.mongodb.com/api/atlas/v2/groups/{groupId}/clusters/{clusterName}/search/indexes/{indexId} | https://cloud.mongodb.com/api/atlas/v2/groups/{groupId}/clusters/{clusterName}/search/indexes/{databaseName}/{collectionName}/{indexName|indexId}" \
     --data'
       {
         "database": "<name-of-database>",
         "collectionName": "<name-of-collection>",
         "type": "vectorSearch",
         "name": "<index-name>",
           "definition": {
             "fields":[ 
               {
                 "type": "vector",
                 "path": <field-to-index>,
                 "numDimensions": <number-of-dimensions>,
                 "similarity": "euclidean | cosine | dotProduct"
               },
               {
                 "type": "filter",
                 "path": "<field-to-index>"
               },
               ...
             }
           ]
         }'

To learn more about the syntax and parameters for the endpoints, see Update One By Name and Update One By ID.

Delete an Atlas Vector Search Index
You can delete an Atlas Vector Search index at any time from the Atlas UI, Atlas Administration API, Atlas CLI, mongosh, or a supported MongoDB Driver.

Required Access
You must have the Project Search Index Editor or higher role to delete an Atlas Vector Search index.

Note
You can use the mongosh command or driver helper methods to delete Atlas Vector Search indexes on all Atlas cluster tiers. For a list of supported driver versions, see Supported Clients.

Procedure
➤ Use the Select your language drop-down menu to select the client you want to use to delete your index.

To delete an Atlas Vector Search index for a collection using the Atlas Administration API, send a DELETE request to the Atlas Search indexes endpoint with either the unique ID or the name of the index to delete.

curl --user "{PUBLIC-KEY}:{PRIVATE-KEY}" --digest \
     --header "Accept: application/json" \
     --include \
     --request DELETE "https://cloud.mongodb.com/api/atlas/v2/groups/{groupId}/clusters/{clusterName}/search/indexes/{indexId} | https://cloud.mongodb.com/api/atlas/v2/groups/{groupId}/clusters/{clusterName}/search/indexes/{databaseName}/{collectionName}/{indexName|indexId}"

To learn more about the syntax and parameters for the endpoint, see Remove One Search Index By Name and Remove One Search Index By ID.

Index Status
When you create the Atlas Vector Search index, the Status column shows the current state of the index on the primary node of the cluster. Click the View status details link below the status to view the state of the index on all the nodes of the cluster.

When the Status column reads Active, the index is ready to use. In other states, queries against the index may return incomplete results.

Status
Description
Not Started

Atlas has not yet started building the index.

Initial Sync

Atlas is building the index or re-building the index after an edit. When the index is in this state:

For a new index, Atlas Vector Search doesn't serve queries until the index build is complete.

For an existing index, you can continue to use the old index for existing and new queries until the index rebuild is complete.

Active

Index is ready to use.

Recovering

Replication encountered an error. This state commonly occurs when the current replication point is no longer available on the mongod oplog. You can still query the existing index until it updates and its status changes to Active. Use the error in the View status details modal window to troubleshoot the issue. To learn more, see Fix Issues.

Failed

Atlas could not build the index. Use the error in the View status details modal window to troubleshoot the issue. To learn more, see Fix Issues.

Delete in Progress

Atlas is deleting the index from the cluster nodes.

While Atlas builds the index and after the build completes, the Documents column shows the percentage and number of documents indexed. The column also shows the total number of documents in the collection.