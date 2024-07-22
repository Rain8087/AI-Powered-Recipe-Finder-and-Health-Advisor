# Author: Jordan Lau Jing Hong
# Student ID: TP064941
# Purpose: FYP

from django.shortcuts import redirect, render
from django.contrib import messages
from .models import myUser
from django.http import JsonResponse
from chatterbot import ChatBot
from django.shortcuts import redirect
from django.contrib import messages
from django.shortcuts import render
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import csv
import re

def register(request):
    if request.method == 'POST':
        # Retrieve username and password from the form data
        username = request.POST.get('username')
        password = request.POST.get('password')
        gender = request.POST.get('gender')


        # Create a new user object and save it to the database
        new_user = myUser.objects.create(username=username, password=password, gender=gender)

        # Render a template displaying the user's ID and password
        return render(request, 'registration_success.html')

    else:
        # Render the registration form
        return render(request, 'register.html')
    
def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        # Check if the username and password match
        user = myUser.objects.filter(username=username, password=password).first()
        if user:
            # Save username in session
            request.session['username'] = username
            return redirect('mainpage')
        else:
            # Handle invalid login
            error_message = 'Invalid username or password'
            return render(request, 'login.html', {'error': error_message})
    else:
        return render(request, 'login.html')
    
def logout_user(request):
    request.session.flush()  # Clear session data
    return render(request, 'login.html')

def mainpage(request):
    # Retrieve the username of the currently logged-in user
    username = request.user.username if request.user.is_authenticated else None
    
    # Pass the username to the template context
    return render(request, 'mainpage.html', {'username': username})

def chatbot_response(request):
    if request.method == 'GET':
        user_input = request.GET.get('message')
        username = request.session.get('username')
        response = ''
        if username:
            try:
                user = myUser.objects.get(username=username)
            except myUser.DoesNotExist:
                return JsonResponse({'response': "User does not exist"})
            
            # Check if the user info is empty
            if not user.age or not user.allergies or not user.chronic_illnesses or not user.dietary_preferences or not user.religious_restrictions:
                # Check if the initial setup message has already been sent
                if not request.session.get('flg_infoSent'):
                    # Send the setup message
                    response = "Hello! It seems like we haven't set up your profile yet. To make sure I can assist you fully, I'll need to gather some information."
                    request.session['flg_infoSent'] = True
                
                # To wait for user response
                request.session['flg_waitResponse'] = 0
                
                # Call the function that handle profile buiding process
                response = handle_profile(request, user_input, user, response)
            elif not request.session.get('flg_recipe_found') or request.session.get('flg_recipe_found') == False:
                # Reset flag to wait user response
                request.session['flg_waitResponse'] = 0
                
                # Check if the initial setup message has already been sent
                if not request.session.get('flg_hintSent'):
                    # User's profile information is complete, continue with the conversation
                    response = "Let's get started on finding your perfect dish! 😊🍽️"
                    request.session['flg_hintSent'] = True
                    response = match_recipes(request, user_input, response)
                else:
                    # Call the function that handle recipe finding
                    response = match_recipes(request, user_input, response)
            elif request.session.get('flg_recipe_found') == True:
                try: # Check if user enter number
                    user_input_number = int(user_input)
                    if 1 <= user_input_number <= 5: # Check if the input is between 1 and 5
                        # Retrieve recipe list from session
                        top_recipes = request.session.get('top_recipes', [])
                        selected_recipe_name = top_recipes[user_input_number - 1]
                        # Store selected recipe in session
                        request.session['selected_recipe'] = selected_recipe_name
                        # Call the function that handles recipe viewing
                        response += view_recipes(request, selected_recipe_name, response)
                    else: # If not, hint user to only choose 1 to 5
                        response = "Please choose from 1 to 5."
                except ValueError:
                    if user_input.lower() == "new": # Check if the input is "new" or "New"
                        request.session['flg_recipe_found'] = False # Set the flag to False to reset status
                        response = "You chose to search for a new recipe.<meta http-equiv='refresh' content='1'>" # Refresh page to prevent confusion
                    elif user_input.lower() == "shopping list" or user_input.lower() == "sl":
                        if not request.session['shopping_list']: # Check if shopping_list is available in session
                            response = "You haven't select a recipe to be added."
                        else:
                            response = save_shopping_list(request, user, response) # Call the function to save shopping list into model
                    else:
                        response = "Please enter the number of the recipe that you wish to view or enter 'new' if you wish to search for a new recipe."

            # Return the response as JSON
            return JsonResponse({'response': response})
        else:
            return JsonResponse({'response': "User is not authenticated"})

# For profile building
def handle_profile(request, user_input, user, response):
    # Check if age is empty
    if not user.age and request.session['flg_waitResponse'] == 0:
        response = profile_age(request, user_input, user, response)
        user_input = ""
    
    # Check if pregnancy is empty and user is female
    # 12 is the theorically age that female can start get pregnant
    if user.gender == 'F' and user.age is not None and user.age >= 12 and not user.pregnancy and request.session['flg_waitResponse'] == 0:
        response = profile_pregnancy(request, user_input, user, response)
        user_input = ""

    # Check if allergies is empty
    if not user.allergies and request.session['flg_waitResponse'] == 0:
        response = profile_allergies(request, user_input, user, response)  
        user_input = ""
            
    # Check if chronic_illnesses is empty
    if not user.chronic_illnesses and request.session['flg_waitResponse'] == 0:
        response = profile_chronic_illnesses(request, user_input, user, response)
        user_input = ""
        
    # Check if dietary_preferences is empty
    if not user.dietary_preferences and request.session['flg_waitResponse'] == 0:
        response = profile_dietary_preferences(request, user_input, user, response)
        user_input = ""
        
    # Check if religious_restrictions is empty
    if not user.religious_restrictions and request.session['flg_waitResponse'] == 0:
        response = profile_religious_restrictions(request, user_input, user, response) 
        user_input = ""
            
    # If all necessary information has been collected, proceed with the conversation
    if user.age and user.allergies and user.chronic_illnesses and user.dietary_preferences and user.religious_restrictions and request.session['flg_waitResponse'] == 0:
        response += "<br>Thank you for sharing your information. Let's get started on finding your perfect dish! 😊🍽️"
        # Prompt user for their preferred ingredient
        response += "<br>What ingredient would you like to have in your dish for today?"
    return response

def profile_age(request, user_input, user, response):
    request.session['flg_waitResponse'] = 1
    # Parse user input to identify age
    identified_age, age_category = parse_age(user_input)
    if identified_age:
        user.age = identified_age
        user.save()
        request.session['flg_waitResponse'] = 0
        # Find user age category
        response += f"Thank you for sharing. Your age category is: {age_category}. Let's continue!"
    else:
        response += "<br>What is your age?"
    return response

def parse_age(user_input):
    """
    Extract age information from user input.
    """
    words = user_input.lower().split()  # Split user input into words
    age = None

    # Iterate over the words in the input
    for i, word in enumerate(words):
        # Check if the word represents a numerical value
        if word.isdigit():
            # Check if the previous word is "not"
            if i > 0 and words[i - 1] == "not":
                continue  # Skip this number as it is negated
            age = int(word)
            break
        
    # Classify age into categories
    if age is not None:
        if age < 3:
            age_category = "Infant"
        elif age < 6:
            age_category = "Toddler"
        elif age < 13:
            age_category = "Child"
        elif age < 20:
            age_category = "Teenager"
        elif age < 40:
            age_category = "Young Adult"
        elif age < 60:
            age_category = "Adult"
        elif age < 80:
            age_category = "Senior"
        else:
            age_category = "Elderly"
    else:
        age_category = None
    return age, age_category

def profile_pregnancy(request, user_input, user, response):
    request.session['flg_waitResponse'] = 1
    # Identify pregnancy mentioned by the user
    identified_pregnancy = []
    for pregnancy in ['yes', 'y', 'no', 'n']:
        if pregnancy in user_input.lower():
            if pregnancy in ['yes', 'y']:
                identified_pregnancy.append('T')
                user.pregnancy = 'T' # Setting it using this method because above one don't work somehow
            elif pregnancy in ['no', 'n']:
                identified_pregnancy.append('F')
                user.pregnancy = 'F' # Setting it using this method because above one don't work somehow
    if identified_pregnancy:
        user.save()
        request.session['flg_waitResponse'] = 0
        response += "Thank you for sharing. Let's continue!"
    else:
        response += "<br>Are you currently pregnant? (Yes/No)"
    return response

def profile_allergies(request, user_input, user, response):
    request.session['flg_waitResponse'] = 1
    # Parse user input to identify allergies
    identified_allergies = parse_allergies(user_input)
    if identified_allergies:
        user.allergies = identified_allergies
        user.save()
        request.session['flg_waitResponse'] = 0
        response += "Thank you for sharing. Let's continue!"
    else:
        response += "<br>Do you have any other food allergies?"
    return response

def parse_allergies(user_input):
    """
    Parse user input to identify allergies mentioned.
    """
    # Define a list of common allergens
    allergens = ['milk', 'egg', 'crustacean shellfish', 'fish', 'peanut', 'no']

    # Initialize a dictionary to store combined allergens
    combined_allergens = {
        'crustacean shellfish': ['crustacean', 'shellfish', 'prawn']
    }

    # Initialize an empty list to store identified allergies
    identified_allergies = []

    # Split user input into words and iterate over them
    words = user_input.lower().split()
    exclude_allergens = False

    # Check for combined allergens first
    for combined_allergen, substrings in combined_allergens.items():
        if any(substring in words for substring in substrings):
            identified_allergies.append(combined_allergen)

    # Then check for individual allergens
    for word in words:
        if word == 'not':
            break
        else:
            if word == 'prawn' or word == 'shellfish':
                if 'crustacean shellfish' not in identified_allergies:
                    identified_allergies.append('crustacean shellfish')
            else:
                for allergen in allergens:
                    if allergen in word:
                        if not exclude_allergens:
                            identified_allergies.append(allergen)
                        else:
                            if allergen in identified_allergies:
                                identified_allergies.remove(allergen)
                        break
    return identified_allergies

def profile_chronic_illnesses(request, user_input, user, response):
    request.session['flg_waitResponse'] = 1
    # Parse user input to identify chronic illnesses
    identified_illnesses = parse_illnesses(user_input)
    if identified_illnesses:
        user.chronic_illnesses += identified_illnesses
        user.save()
        request.session['flg_waitResponse'] = 0
        response += "Thank you for sharing. Let's continue!"
    else:
        response += "<br>Do you have any chronic illnesses that I should know about?"

    return response

def parse_illnesses(user_input):
    """
    Parse user input to identify chronic illnesses mentioned.
    """
    # Define a list of common chronic illnesses
    illnesses = ['diabetes', 'hypertension', 'no']

    # Initialize a dictionary to store combined illnesses
    combined_illnesses = {
        'diabetes': ['diabetes'],
        'hypertension': ['hypertension', 'high'],
        'cardiovascular disease': ['heart', 'cardiovascular disease, cardiovascular'],
        'kidney disease': ['chronic kidney disease', 'kidney disease', 'kidney']
    }

    # Initialize an empty set to store identified illnesses
    identified_illnesses = set()

    # Split user input into words and iterate over them
    words = user_input.lower().split()
    exclude_illnesses = False

    # Check for combined illnesses first
    for combined_illness, substrings in combined_illnesses.items():
        if any(substring in words for substring in substrings):
            identified_illnesses.add(combined_illness)

    # Then check for individual illnesses
    for word in words:
        if word == 'not':
            exclude_illnesses = True
        elif exclude_illnesses:
            # Exclude illnesses mentioned after 'not'
            for ill in illnesses:
                if ill in word:
                    if ill in identified_illnesses:
                        identified_illnesses.remove(ill)
            exclude_illnesses = False
        else:
            for ill in illnesses:
                if ill in word:
                    identified_illnesses.add(ill)

    return list(identified_illnesses)

def profile_dietary_preferences(request, user_input, user, response):
    request.session['flg_waitResponse'] = 1
    # Parse user input to identify chronic illnesses
    identified_preferences = parse_dietary_preferences(user_input)
    if identified_preferences:
        user.dietary_preferences += identified_preferences
        user.save()
        request.session['flg_waitResponse'] = 0
        response += "Thank you for sharing. Let's continue!"
    else:
        response += "<br>Are there any dietary preferences you'd like me to consider?"

    return response

def parse_dietary_preferences(user_input):
    """
    Parse user input to identify dietary preferences mentioned.
    """
    # Define a list of common dietary preferences
    preferences = ['vegetarian', 'vegan', 'gluten-free', 'dairy-free', 'low-carb', 'no']

    # Initialize an empty set to store identified preferences
    identified_preferences = set()

    # Split user input into words and iterate over them
    words = user_input.lower().split()

    # Check for dietary preferences
    for word in words:
        if word == 'not':
            break
        else:
            for preference in preferences:
                if preference in word:
                    identified_preferences.add(preference)
    return identified_preferences

def profile_religious_restrictions(request, user_input, user, response):
    request.session['flg_waitResponse'] = 1
    # Identify religious affiliation mentioned by the user
    identified_religious = None

    # Define valid religious affiliations
    valid_religions = ['islam', 'hinduism', 'buddhism', 'christianity']

    # Check if user input matches a valid religious affiliation
    for religion in valid_religions:
        if religion in user_input.lower():
            identified_religious = religion
            break

    if identified_religious:
        # Update user's religious restriction
        user.religious_restrictions = identified_religious
        user.save()
        request.session['flg_waitResponse'] = 0
        response += "Thank you for sharing your information. We have finish building your profile."
    else:
        # Prompt for religious affiliation
        response += "<br>What is your religious affiliation? (Islam, Hinduism, Buddhism, or Christianity)"
    return response

# For recipe finding
def match_recipes(request, user_input, response):
    try:
        request.session['flg_waitResponse'] = 0
        
        # Read the dataset
        data = pd.read_excel("login/data/model training data FULL.xlsx")
        X = data['NER'].astype(str)  # Ingredients
        y = data['title']  # Recipe titles
        
        # Filter out ingredients based on user profile
        filtered_ingredients = set()
        username = request.session.get('username')
        user = myUser.objects.get(username=username)
        # Filter out ingredients based on pregnancy status
        pregnancy = user.pregnancy
        pregnancy_allergenic_ingredients = {
            'caffeine': ['coffee', 'tea', 'soda', 'chocolate'],
            'raw seafood': ['sushi', 'oysters', 'clams', 'sashimi'],
            'others': ['alcohol', 'herbs'],
        }
        if pregnancy:
            for allergen in pregnancy_allergenic_ingredients:
                filtered_ingredients.update(pregnancy_allergenic_ingredients[allergen])
        # Filter out ingredients based on user allergies
        allergies = user.allergies
        allergenic_ingredients = {
            'milk': ['milk', 'butter', 'cheese', 'cream', 'yogurt'],
            'egg': ['egg', 'mayonnaise', 'baked goods', 'noodles'],
            'crustacean shellfish': ['shrimp', 'lobster', 'crab', 'prawns', 'crayfish'],
            'fish': ['fish', 'salmon', 'tuna', 'cod', 'trout'],
            'peanut': ['peanut', 'peanut butter', 'peanut oil', 'peanut flour']
        }
        for allergen in allergies:
            filtered_ingredients.update(allergenic_ingredients.get(allergen, []))
            
        # Filter out ingredients based on chronic illnesses
        chronic_illnesses = user.chronic_illnesses
        chronic_illness_ingredients = {
            'diabetes': ['sugar', 'honey', 'candy', 'soda'],
            'hypertension': ['salt', 'processed foods', 'fast food', 'fatty meats'],
            'cardiovascular': ['trans fats', 'fried foods', 'saturated fats', 'processed meats'],
            'kidney disease': ['high phosphorus foods', 'high potassium foods', 'high sodium foods']
        }
        for illness in chronic_illnesses:
            filtered_ingredients.update(chronic_illness_ingredients.get(illness, []))
            
        # Filter out ingredients based on user dietary preference
        dietary_preferences = user.dietary_preferences
        dietary_preference_ingredients = {
            'vegetarian': ['beef', 'chicken', 'bacon', 'turkey'],
            'vegan': ['beef', 'chicken', 'bacon', 'turkey', 'egg', 'milk', 'cheese'],
            'gluten-free': ['wheat', 'barley', 'rye', 'bread', 'pasta'],
            'dairy-free': ['milk', 'butter', 'cheese', 'cream', 'yogurt'],
            'low-carb': ['pasta', 'rice', 'potatoes', 'bread', 'sugar']
        }
        for preference in dietary_preferences:
            if preference in dietary_preference_ingredients:
                filtered_ingredients.update(dietary_preference_ingredients[preference])
        
        # Filter out ingredients based on user religious restriction
        religious_restrictions = user.religious_restrictions
        religious_ingredients = {
            'islam': ['pork','bacon', 'alcohol'],
            'hinduism': ['beef', 'alcohol'],
            # 'buddhism': ['none'],
            # 'christianity': ['none'],
        }
        filtered_ingredients.update(religious_ingredients.get(religious_restrictions, []))
        
        # Display for debug purpose
        print("Filtered Ingredients:", filtered_ingredients)

        # Match recipes based on user input
        if user_input.strip():
            top_recipes = parse_ingridients(user_input,y, X, allergen, filtered_ingredients)
            request.session['top_recipes'] = top_recipes
            request.session['flg_waitResponse'] = 1
        else:
            request.session['flg_waitResponse'] = 0 

        # Prepare response
        if request.session['flg_waitResponse'] == 1 and request.session.get('top_recipes'):
            response = "Top 5 matching recipes:<br>"
            for i, recipe in enumerate(request.session['top_recipes'], 1):
                response += f"{i}. {recipe}<br>"
            response += "<br>Please enter the number or name of the recipe to choose the recipe you wish to view."
            request.session['flg_recipe_found'] = True
        else:
            response = "Please enter the ingredients you wish to have in your dish, separated by commas(,). <br>If you want to exclude certain ingredients, you can type 'no' followed by those ingredients."
            request.session['flg_recipe_found'] = False
    except myUser.DoesNotExist:
        response = "User does not exist."
    except Exception as e:
        response = f"An error occurred: {str(e)}"
    return response

def parse_ingridients(user_input,y, X, allergen, filtered_ingredients):
    # Extract user-excluded terms
    user_exclude = []
    user_ingredients = []
    split_input = user_input.split(",")
    for term in split_input:
        if term.strip().lower().startswith('no'):
            exclude_term = term.strip().lower().lstrip('no').strip()
            user_exclude.append(exclude_term)
        else:
            user_ingredients.append(term)
    print("Include Ingredients:", user_ingredients)
    print("Exclude Ingredients:", user_exclude)
    # Remove recipes containing allergenic ingredients from the list
    X_filtered = []
    y_filtered = []
    for recipe_ingredients, recipe_title in zip(X, y):
        if not any(allergen in recipe_ingredients.lower() for allergen in filtered_ingredients):
            X_filtered.append(recipe_ingredients)
            y_filtered.append(recipe_title)


    # Vectorize ingredients
    vectorizer = TfidfVectorizer()
    X_transformed = vectorizer.fit_transform(X_filtered)
    # Predict Matching Recipes
    user_input_transformed = vectorizer.transform(user_ingredients)
    similarities = cosine_similarity(user_input_transformed, X_transformed)
    # Find indices of recipes that match the exclusion criteria
    exclude_indices = []
    for term in user_exclude:
        exclude_indices.extend([idx for idx, recipe in enumerate(X) if term in recipe.lower()])
    # Filter out recipes from top_indices that match the exclusion list
    filtered_indices = [idx for idx in similarities.argsort(axis=1)[0][-10:][::-1] if idx not in exclude_indices]
    # Get the recipes corresponding to the filtered indices
    top_recipes = [y[idx] for idx in filtered_indices[:5]]  # Select top 5 recipes from filtered indices
    return top_recipes

def view_recipes(request, selected_recipe_name, response):
    # Read the dataset
    csv_file_path = "login/data/Recipe_Cleaned.csv"
    response += "Sorry for taking so long to retrieve the recipe."
    
    # Read the CSV file and store the data in a list
    recipe_data = []
    with open(csv_file_path, "r", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            recipe_data.append(row)

    # Find the row where the 'title' matches the selected_recipe_name
    selected_recipe = None
    for recipe in recipe_data:
        if selected_recipe_name == recipe['title']:
            selected_recipe = recipe
            break

    if selected_recipe:
        # Display the selected recipe title
        response += f"<br>{selected_recipe['title']}<br>"
        # Save ingredients into session
        ingredients_str = f"{selected_recipe['title']}"
        history_str = f"{selected_recipe['title']}|"
        ingredients = re.findall(r'"([^"]*)"', selected_recipe['ingredients'])
        for ingredient in ingredients:
            ingredients_str += f"| {ingredient}; 0"
            history_str += f"{ingredient};"
        request.session['shopping_list'] = ingredients_str
        history_str += "|"
        
        # Display the ingredients
        response += "<b>Ingredients</b><br>"
        ingredients = re.findall(r'"([^"]*)"', selected_recipe['ingredients'])
        for ingredient in ingredients:
            response += f"- {ingredient}<br>"
        
        # Display the directions
        response += "<br><b>Directions</b><br>"
        directions = re.findall(r'"([^"]*)"', selected_recipe['directions'])
        history_str += f"{directions}"
        if len(directions) == 1:
            directions = selected_recipe['directions'].strip("[]").replace("'", "").split(". ")
            for i, direction in enumerate(directions, 1):
                direction = direction.strip().encode('utf-8').decode('unicode-escape')
                response += f"{i}. {direction.replace('\"', '')}.<br>"
        else:
            for i, direction in enumerate(directions, 1):
                direction = direction.strip().encode('utf-8').decode('unicode-escape')
                response += f"{i}. {direction}<br>"
        
        request.session['history'] = history_str
        
        # Display the recipe link
        response += f"<br><b>Recipe Link</b> <br>{selected_recipe['link']}"
        response += "<br><br>Enter 'shopping list' if you wish to have a shopping list for this recipe."
        response += "<br>Or enter another number to view another recipe"
    return response

# For shopping list
def save_shopping_list(request, user, response):
    # Check if the user's shopping list has reached the maximum length of 5
    if len(user.shopping_list) >= 5:
        response += "You have reached the maximum limit of 5 shopping lists. You cannot add more."
    else:
        # Get the shopping list item and history from the session
        shopping_list_item = request.session.get('shopping_list')
        new_history = request.session.get('history')
        
        # Check if the shopping list item already exists in the user's shopping list
        if shopping_list_item not in user.shopping_list:
            # Append the shopping list item to the user's shopping list
            user.shopping_list.append(shopping_list_item)
            response += f"The ingredients of '{request.session['selected_recipe']}' have been successfully added to your shopping list."
        else:
            response += f"The ingredients of '{request.session['selected_recipe']}' are already in your shopping list."
        
        # Check if the item already exists in the history before appending
        if new_history not in user.history:
            user.history.append(new_history)
        else:
            # If the item already exists, remove it before appending
            user.history.remove(new_history)
            user.history.append(new_history)
        
        # Save the user object to update the shopping list and history
        user.save()
    
    return response

def shopping_list(request):
    username = request.session.get('username')
    user = myUser.objects.get(username=username)
    shopping_list = []

    # Iterate over each item in the user's shopping list
    for item in user.shopping_list:
        # Split the item into title and ingredients with conditions
        parts = item.split("|")
        title = parts[0].strip()
        ingredients_with_conditions = [ingredient_condition.split("; ") for ingredient_condition in parts[1:]]
        shopping_list.append({'title': title, 'ingredients': ingredients_with_conditions})

    return render(request, 'shopping_list.html', {'shopping_list': shopping_list})

def shopping_list_remove(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        username = request.session.get('username')
        
        try:
            user = myUser.objects.get(username=username)
            shopping_list = user.shopping_list
            
            # Filter out the item with the given title
            filtered_list = []
            for item in shopping_list:
                # Split the item string by "|" to get the title
                item_title = item.split("|")[0]
                if item_title.strip() != title.strip():
                    filtered_list.append(item)
            
            # Update the shopping list
            user.shopping_list = filtered_list
            user.save()
            
            messages.success(request, 'Item removed successfully.')
        except myUser.DoesNotExist:
            messages.error(request, 'User not found.')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
        
    return redirect('shopping_list')

# For history
def history(request):
    # Retrieve the username from the session
    username = request.session.get('username')
    user = myUser.objects.get(username=username)
    history_recipes = user.history
    
    # Preprocess the recipes to extract titles separately
    processed_recipes = [{'title': recipe.split('|')[0], 'details': '|'.join(recipe.split('|')[1:])} for recipe in history_recipes]
    
    context = {
        'history_recipes': processed_recipes
    }
    return render(request, 'history.html', context)


# Edit account
def edit_account(request):
    # Retrieve the username from the session
    username = request.session.get('username')
    user = myUser.objects.get(username=username)
    
    return render(request, 'edit_account.html', {'user': user})

def edit_account_update(request):
    # Retrieve the username from the session
    username = request.session.get('username')
    user = myUser.objects.get(username=username)

    # Update the user's account details
    new_password = request.POST.get('password')
    
    # Update password
    user.password = new_password
    user.save()

    # Redirect to the main page
    success_message = 'Password successfully change'
    return render(request, 'edit_account.html', {'user': user, 'success': success_message})