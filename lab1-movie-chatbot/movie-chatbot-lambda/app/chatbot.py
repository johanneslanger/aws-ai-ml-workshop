"""
This sample demonstrates an implementation of the Lex Code Hook Interface
in order to serve a sample bot which servers movie recommendations absed on a similar movie
"""
import math
import datetime
import logging
import boto3
import os
import csv 
import json

""" --- Static initialization--- """
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

if os.environ['CAMPAIGN_ARN']: # we only care about these items when integrating with Personalize
    logger.debug('We will be integrating with Amazon Personalize now')
    campaign_arn = os.environ['CAMPAIGN_ARN'] # the arn of the campaign to call in Amazon Personalize
    assets_bucket = os.environ['ASSETS_BUCKET'] # the bucket which contains static assets

    ## Let's make sure that the bucket exists
    s3 = boto3.client('s3')
    if s3.head_bucket(Bucket=assets_bucket):
        logger.debug("The bucket "+ assets_bucket+ " exists, let's move on")
    elif assets_bucket: ## the variable will be empty at first, so we need to make sure to account for that
        raise Exception("The bucket " + assets_bucket + " does not exist. Please enter in an S3 bucket in the form of: movie-chatbot-resources-(your account number without hyphens, only digits)")
    
    ## Initialize the content
    if os.environ.get('MOVIE_DATA_OBJECT') is None:
        movie_data_object = 'movies.csv' # the object in the s3 bucket which has the list of movie titles and IDs
    else:
        movie_data_object = os.environ['MOVIE_DATA_OBJECT']
    movies_file_local = '/tmp/movies.csv' # where to cache the file locally
    logger.debug(
    'Initializing lambda with campaign: {}, bucket: {}, movie_data:{}, file: {}'.format(campaign_arn,assets_bucket, movie_data_object, movies_file_local))
    """ --- download the movies file --- """
    # First we need to download a list of possible movies so we can match them to an item id which can be used to call Amazon Personalize
  
    logger.debug(
    'Downloading movies list from url=s3://{}/{}'.format(assets_bucket, movie_data_object))
    s3.download_file(assets_bucket, movie_data_object, movies_file_local)
    # Read in CSV file and create simple lookup dictionary, we could use pandas, however this pulls in a huge dependency and we want to keep it simple for this demo
    moviesDict = {}
    movies = csv.DictReader(open("/tmp/movies.csv"))
    for row in movies:
        moviesDict.update({row['ITEM_ID'] : {'id': row['ITEM_ID'], 'title': row['title'], 'genre': row['genre']}})

""" --- Helpers functions --- """
def get_slots(intent_request):
    return intent_request['currentIntent']['slots']

def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def searchMovieByTitle(movies, title):
    """
    We search for the title with a simple string match in our list movie titles. Keeping it simple, as this is jsut a demo!
    """
    for k in movies:
        if title.lower() in movies[k]['title'].lower():
            return movies[k]
    return None

def get_recommendations_for_movie(watchedMovie):
    """
    Gets a list of similar movies from a trained model in Amazon Personalize
    """
    logger.debug('get_recommendations_for_movie={}'.format(watchedMovie))
    client = boto3.client('personalize-runtime')
    rec_Items = []
    
    ## change this so that we ignore pesonalize endpoint existence if not provided
    movieItem = searchMovieByTitle(moviesDict, watchedMovie)
    logger.debug('Matched to item={}'.format(movieItem))
    rec_response = client.get_recommendations(
        campaignArn=campaign_arn,
        itemId=str(movieItem['id']),
        numResults=5
    )
    rec_itemIds = [x['itemId'] for x in rec_response['itemList']] # parse ItemIds from response
    logger.debug('Personalize returned following ids:={}'.format(rec_itemIds))

    for itemId in rec_itemIds:
        rec_Items.append(moviesDict[itemId])
    
    logger.debug('Returning recommendations:={}'.format(rec_Items))
    return rec_Items


def get_fulfilled_message(rec_Items):
    responseMessage = 'Thanks, Here is a list of movies I would recommend:'
    for movie in rec_Items:
        responseMessage = responseMessage + \
        ',\n' + movie['title'] 
    return responseMessage + '.\n Enjoy!'


""" --- Function that control the bot's behavior --- """
def recommend_movies(intent_request):
    """
    Extracts the watched Movie from the intent, calls Personalize to get similar movies and returns the 5 most recommended movies!
    """

    watchedMovie = get_slots(intent_request)["watchedMovie"]
    if os.environ['CAMPAIGN_ARN']:
        recommendations = get_recommendations_for_movie(watchedMovie)
        message = get_fulfilled_message(recommendations)
        return close(intent_request['sessionAttributes'],
            'Fulfilled',
            {'contentType': 'PlainText',
            'content': message})
    else:
        message = 'Right now, I am feeling under the weather and cannot provide a movie suggestion.'
        return close(intent_request['sessionAttributes'],
        'Fulfilled',
        {'contentType': 'PlainText',
            'content': message})

def dispatch(intent_request):
    """
    Dispatch function In case you want to support multiple intents with a single lambda function
    """

    logger.debug('dispatch userId={}, intentName={}'.format(
        intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == os.environ['INTENT_NAME']:
        return recommend_movies(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported, because it is not equal to the value set for environment variable INTENT_NAME: '+ os.environ['INTENT_NAME'])


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """

    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)
