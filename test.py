import sys

print("This is a test script which fires based on code commit done in SwagLabs Repo")

pr_num_from_arg = sys.argv[1]

print("pr_num_from_arg=",pr_num_from_arg)

pr_num_from_env_var = os.getenv('PR_NUMBER')
print("pr_num_from_env_var=",pr_num_from_env_var)