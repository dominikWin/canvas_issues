import datetime
import json

import canvasapi
import github
import boto3

s3_client = boto3.client('s3')

def log(config, msg, level='INFO'):
    msg = "[{}] {}: {}".format(level, datetime.datetime.now().isoformat(), msg)
    print(msg)
    config['data']['logs'].append(msg)

def encode_assignment(course, assignment):
    obj = {
            'course': course.name,
            'name': assignment.name,
            'due_at': assignment.due_at,
            'url': assignment.html_url
        }
    return obj

def execute(config):
    try:
        canvas = canvasapi.Canvas(config["CANVAS_API_URL"], config["CANVAS_API_KEY"])
        for course in canvas.get_courses():
            if config["COURSE_CODE_FILTER"] in course.course_code:
                for assignment in course.get_assignments():
                    obj = encode_assignment(course, assignment)
                    if str(assignment.id) in config['data']['assignments']:
                        if obj != config['data']['assignments'][str(assignment.id)]:
                            log(config, "Assignment {} changed: {}".format(assignment.id, json.dumps(obj)))
                            config['data']['assignments'][str(assignment.id)] = obj
                    else:
                        log(config, "Found new assignment {}: {}".format(assignment.id, json.dumps(obj)))
                        config['data']['assignments'][str(assignment.id)] = obj
                        
                        title = assignment.name
                        body = "[{}]({}) - {}\n\nDue {}".format(obj['name'], obj['url'], obj['course'], obj['due_at'])
                        hub = github.Github(config["GITHUB_TOKEN"])
                        repo = hub.get_repo(config["GITHUB_REPO"])
                        
                        # print('dry run {}: {}'.format(title, body))
                        issue = repo.create_issue(title, body)
                        issue_id = issue.id
                        log(config, "Created github issue {}".format(issue_id))
    except Exception as e:
        log(config, 'Error: {}'.format(e), level='ERR')
    return config

def lambda_handler(event, context):
    data = s3_client.get_object(Bucket='some-bucket.db', Key='app.json')['Body'] \
        .read() \
        .decode('utf-8')
    cfg = json.loads(data)
    cmp_cfg = json.loads(data)
    cfg = execute(cfg)
    if cfg != cmp_cfg:
        print('Changed output! Updating s3')
        data = json.dumps(cfg, sort_keys=True, indent=4, separators=(',', ': '))
        data = data.encode('utf-8')
        s3_client.put_object(Bucket='some-bucket.db', Key='app.json', Body=data)
    else:
        print('No change found, done')
