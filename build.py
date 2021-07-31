import gitlab
import questionary
from libraries.gl_functions import *

gl_url = input('Your Gitlab Server Location\nex: https://gitlab.yourcompany.com :  ')
gl_token = input('Your Gitlab Private Access Token: ')
gl = gitlab.Gitlab(gl_url, private_token=gl_token)
# Start by finding top-level groups user has access to
groups = gl.groups.list(top_level_only=True)
# We'll build a list of dictionaries for each
# top-level group the user has access to.

top_group_details = get_prigroup_details(groups)
selected_group_id = top_group_details[1]
selected_group_name = top_group_details[0]
top_group_id = top_group_details[1]
top_group_name = top_group_details[0]

select_target_group = \
  find_target_group(
    gl, selected_group_name, selected_group_id, groups)
target_group_name = select_target_group[0]
target_group_id = select_target_group[1]

# now that we're done figuring out where to build a project,
# let's go build a project, shall we?
new_project_name = project_init(
  target_group_id, target_group_name, gl)
create_project = gl.projects.create(
    {'name': new_project_name, 'namespace_id': target_group_id})
group = gl.groups.get(
    target_group_id)
projects = group.projects.list()
project_list = []
for project in projects:
    project_id = (project.id)
    project_name = (project.name)
    project_url = (project.web_url)
    project_list.append({'name': project_name, 'id': project_id})
project_name = [name['name'] for name in project_list]
new_project_id = next(
  project['id'] for project in project_list
  if project['name'] == new_project_name)
project = gl.projects.get(new_project_id)
# TODO: figure out why we aren't being prompted for adding users
more_users = True
add_users_confirm = questionary.confirm(
    'Would you like to add additional users to '
    + str(new_project_name) + ' ?\n'
    'Note: users who are already members of '
    + str(target_group_name) + 'or ' + str(top_group_name) + ' are already members by default').ask()
if add_users_confirm is True:
    user_found = False
    while more_users:
        while not user_found:
            user_search = questionary.text(
                'Please supply a user to search for (real names only, emails cannot be searched) :').ask()
            user_search_result = gl.users.list(as_list=False, search=user_search)
            found_users = []
            for user in user_search_result:
                user_real_name = (user.name)
                user_name = (user.username)
                user_id = (user.id)
                found_users.append({'realname':user_real_name, 'glusername': user_name, 'gluserid':user_id})
                found_user_choices = [realname['realname'] for realname in found_users]
                print(found_user_choices)
                found_user_choices.append('None of these users')
                selected_user = questionary.select('The following users have been found using ' + str(user_search) + ' as a search term\n which of these would you like to add to ' +str(new_project_name) +'?',
                choices = found_user_choices
                ).ask()
            if selected_user == 'None of these users':
                user_found = False
            else:
                user_found = True
            selected_user_id = next(user['gluserid'] for user in found_users if user['realname']== selected_user)
            user_access_level = questionary.select('What level of access would you like to grant ' + str(selected_user) + ' to ' + str(new_project_name) + '?',
                choices = [
                'Maintainer',
                'Developer'
                ]
                ).ask()
            if user_access_level == 'Maintainer':
                project_access_level = gitlab.MAINTAINER_ACCESS
            if user_access_level == 'Developer':
                project_access_level = gitlab.DEVELOPER_ACCESS
            project.members.create({'user_id': selected_user_id, 'access_level': project_access_level})
            add_additional_users = questionary.confirm('Would you like to add more users to ' + str(new_project_name) + '?').ask()
            if add_additional_users is True:
                more_users = True
            else:
                more_users = False
# Create the default branches, remove master, set main as default
create_default_branches = create_branches(project, new_project_id, gl_token, gl_url)
main_branch_id = create_default_branches[0]
test_branch_id = create_default_branches[1]
development_branch_id = create_default_branches[2]
# Create approval rules for each branch, finish things up.
create_approval_rules(top_group_id, main_branch_id, test_branch_id, development_branch_id, new_project_id, gl_token, gl_url)
#Crap: path isn't returning like I thought it would
#path = [project['web_url'] for project in project_list if project['name'] == new_project_name]
print('Congratualations! You have successfuly built ' + str(new_project_name)) # + '\nYour new project can be found at ' + str(path))
