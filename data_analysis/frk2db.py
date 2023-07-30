from FreakingAwesomeCLI.CLI import convert_sql_impl

db_list = [[f'/mnt/e/tracing_path/otrace{i}', f'/mnt/e/tracing_path/db/db{i}'] for i in range(30)]

[convert_sql_impl(input_dir = db[0], output = db[1]) for db in db_list]
