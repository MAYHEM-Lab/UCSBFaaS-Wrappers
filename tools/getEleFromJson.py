import json,argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parser')
    parser.add_argument('str_hierarchy',action='store',help='colon delimited hierarchy, e.g. foo says extract obj["foo"], foo:bar says extract obj["foo"]["bar"]')
    parser.add_argument('json_file',action='store',help='output json from aws dynamodb create-table')
    parser.add_argument('--multiple',action='store_true',default=False,help='look for multiple secondary options and return space separated string')
    args = parser.parse_args()
    sp = args.str_hierarchy.split(':')
    dep = len(sp)
    retn = ''
    with open(args.json_file,'r') as f:
        j = json.load(f)
        if args.multiple:
            assert dep == 2 #only depth of 2 currently handled
            for ele in j[sp[0]]:
                if retn == '':
                    retn = ele[sp[1]]
                else: 
                    retn += ' {}'.format(ele[sp[1]])
        else:
            if dep == 1:
                print(j[sp[0]])
            elif dep == 2:
                print(j[sp[0]][sp[1]])
            elif dep == 3:
                print(j[sp[0]][sp[1]][sp[2]])
            else: 
                print("ERROR, unable to handle a depth of greater than 3")
    if retn != '':
        print(retn)

