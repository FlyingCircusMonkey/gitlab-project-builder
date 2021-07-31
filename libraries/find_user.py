import gitlab

gl_url = input('Your Gitlab Server Location\nex: https://gitlab.yourcompany.com :  ')
gl_token = input('Your Gitlab Private Access Token: ')
gl = gitlab.Gitlab(gl_url, private_token= gl_token)
user_search = input('user to search for: ')
users = gl.users.list(as_list=False, search=user_search)
for user in users:
    user_real_name = (user.name)
    user_name = (user.username)
    user_id = (user.id)
    print('Real Name : ' + str(user_real_name) +'\nGitlab Username : ' + str(user_name) + '\nUser ID : ' + str(user_id) )
