import questionary
import requests
import gitlab
import re

def get_prigroup_details(groups):
    topgroups = []
    for group in groups:
        group_name = (group.name)
        group_id =(group.id)
        group_url = (group.web_url)
        group_path = (group.path)
        topgroups.append({
                            'name':group_name,
                            'id':str(group_id),
                            'url':group_url,
                            'path':group_path}
                            )
    top_group_name = str(questionary.select(
        "Below are the top-level groups you may build a project in\nWhich one should be your primary group?",
        choices = [name['name'] for name in topgroups]
    ).ask())
    top_group_id = next(group['id'] for group in topgroups if group['name']== top_group_name)
    return top_group_name, top_group_id

def find_target_group(gl, selected_group_name, selected_group_id, groups):
    target_group_found = False
    while not target_group_found:
        group = gl.groups.get(selected_group_id)
        subgroup = group.subgroups.list(as_list=True)
        if subgroup:
            subgroups = []
            for subgroup in subgroup:
                group_name = (subgroup.name)
                group_id = (subgroup.id)
                subgroups.append({'name': group_name,'id':group_id})
            sub_group_choices = [name['name'] for name in subgroups]
            sub_group_choices.append('Create a project in ' + str(selected_group_name))
            sub_group_choices.append('Create a new subgroup in ' + str(selected_group_name))
            sub_group_name  = str(questionary.select(
                'The following child groups were found in ' +str(selected_group_name) + '\nWhich child group would you like to build a project in?',
                choices = sub_group_choices
                ).ask())
            if sub_group_name == 'Create a project in ' + str(selected_group_name):
                target_group_id = selected_group_id
                target_group_name = selected_group_name
                target_group_found = True
            elif sub_group_name == 'Create a new subgroup in ' + str(selected_group_name):
                group_details = create_new_group(gl, selected_group_id)
                target_group_name = group_details[1]
                target_group_id = group_details[0]
                target_group_found = True

            else:
                selected_group_id = next(group['id'] for group in subgroups if group['name']== sub_group_name)
                selected_group_name = sub_group_name
        else: # If the subgroup list is empty, there are no subgroups in the selected group
            sub_group_name  = str(questionary.select(
                str(selected_group_name) + ' does not contain any child groups, your choices are: ',
                choices = [
                    'Create a project in ' +str(selected_group_name),
                    'Create a new subgroup in ' +str(selected_group_name)
                ]
                ).ask())
            if sub_group_name == 'Create a project in ' + str(selected_group_name):
                target_group_id = selected_group_id
                target_group_name = selected_group_name
                target_group_found = True
            elif sub_group_name == 'Create a new subgroup in ' + str(selected_group_name):
                group_details = create_new_group(gl, selected_group_id)
                target_group_name = group_details[1]
                target_group_id = group_details[0]
                target_group_found = True
    return target_group_name, target_group_id

def create_new_group(gl, target_group_id):
    new_subgroup_name = questionary.text(
                    'What should we call this new subgroup?\nSpaces are allowed, special characters are not\n').ask()
    new_subgroup_name = re.sub('[^A-Za-z0-9 ]+', '', new_subgroup_name)
    new_subgroup_path = new_subgroup_name.lower().replace(" ","_").replace("-","_")
    gl.groups.create({'name': new_subgroup_name, 'path': new_subgroup_path, 'parent_id': target_group_id})
    groups = gl.groups.list(as_list=True, search=new_subgroup_name)
    for subgroup in groups:
        group_name = (subgroup.name)
        group_id = (subgroup.id)
    return group_id, group_name

def project_init(target_group_id, target_group_name, gl):
    group = gl.groups.get(target_group_id)
    projects = group.projects.list(as_list=True)
    target_group_projects = []
    for project in projects:
        project_name = (project.name)
        project_id = (project.id)
        target_group_projects.append({'name':project_name, 'id':project_id})
    new_project_name = questionary.text(
            'What should we call this new project?\nSpaces are allowed, special characters are not\n').ask()
    new_project_name = re.sub('[^A-Za-z0-9 ]+', '',new_project_name)
    existing_projects = [name['name'] for name in target_group_projects]
    valid_name = False
    while not valid_name:
        if new_project_name in existing_projects:
            new_project_name = questionary.text(
                    'It would appear that a project called ' +str(new_project_name) + '\n'\
                    'Is alread in ' +str(target_group_name) + '. Please choose a different name\n' \
                    '\nSpaces are allowed, special characters are not\n').ask()
            new_project_name = re.sub('[\W\_]','',new_project_name)
        else:
            valid_name = True
    return new_project_name

def create_approval_rules(top_group_id, main_branch_id, test_branch_id, development_branch_id, new_project_id, gl_token, gl_url):
    # Create merge rules for the main branch
    main_approval_rule = ({
        "name": 'main',
        "approvals_required": 1,
        "rule_type": "regular",
        "group_ids": top_group_id,
        "protected_branch_ids": int(main_branch_id)
    })
    headers = {
        'PRIVATE-TOKEN': str(gl_token)
        }
    requests.post(gl_url + '/api/v4/projects/' + str(new_project_id) + '/approval_rules/' , headers=headers, params=main_approval_rule)
    
    # Create merge rules for the test branch
    test_approval_rule = ({
        "name": 'test',
        "approvals_required": 1,
        "rule_type": "regular",
        "group_ids": top_group_id,
        "protected_branch_ids": int(test_branch_id)
    })
    headers = {
        'PRIVATE-TOKEN': str(gl_token)
        }
    requests.post(gl_url + '/api/v4/projects/' + str(new_project_id) + '/approval_rules/' , headers=headers, params=test_approval_rule)

    # Create merge rules for the development branch
    development_approval_rule = ({
        "name": 'development',
        "approvals_required": 1,
        "rule_type": "regular",
        "group_ids": top_group_id,
        "protected_branch_ids": int(development_branch_id)
    })

    headers = {
        'PRIVATE-TOKEN': str(gl_token)
    }

    requests.post(gl_url + '/api/v4/projects/' + str(new_project_id) + '/approval_rules/' , headers=headers, params=development_approval_rule)

def create_branches(project, new_project_id, gl_token, gl_url):
    project.branches.create({'branch': 'main', 'ref': 'master'})
    project.protectedbranches.create({
    'name': 'main',
    'merge_access_level': gitlab.MAINTAINER_ACCESS,
    'push_access_level': gitlab.MAINTAINER_ACCESS
    })
    project.branches.create({'branch': 'test', 'ref': 'main'})
    project.protectedbranches.create({
    'name': 'test',
    'merge_access_level': gitlab.MAINTAINER_ACCESS,
    'push_access_level': gitlab.MAINTAINER_ACCESS
    })
    project.branches.create({'branch': 'development', 'ref': 'test'})
    project.protectedbranches.create({
    'name': 'development',
    'merge_access_level': gitlab.DEVELOPER_ACCESS,
    'push_access_level': gitlab.DEVELOPER_ACCESS
    })
    project.default_branch = 'main'
    project.save()
    project.branches.delete('master')
    project.protectedbranches.delete('master')
    project.save()
    headers = {
        'PRIVATE-TOKEN': str(gl_token)
    }
    prot_branches = [] 
    protected_branches = requests.get(gl_url + '/api/v4/projects/' + str(new_project_id) + '/protected_branches/' , headers=headers).json()
    for branch in protected_branches:
        branchname = (branch['name'])
        branchid = (branch['id'])
        prot_branches.append({'name':branchname, 'id':branchid})
    for branch in prot_branches:
        main_branch_id = next(branch['id'] for branch in prot_branches if branch['name']== 'main')
        test_branch_id = next(branch['id'] for branch in prot_branches if branch['name']== 'test')
        development_branch_id = next(branch['id'] for branch in prot_branches if branch['name']== 'development')
    return main_branch_id, test_branch_id, development_branch_id
