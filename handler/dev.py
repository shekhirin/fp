import json
from handler import BaseHandler
import hmac
from hashlib import sha1
import os


class DevHandler(BaseHandler):
    def post(self, url):
        url = url[1:]
        if url.startswith('git'):

            try:
                postdata = json.loads(self.request.body.decode(encoding='utf8'))
            except BaseException:
                return

            if self.request.headers.get('X-Github-Event', '-1') == 'push' \
                    and postdata.get("ref", '').split('/')[-1] == 'master':
                sh0 = self.request.headers.get('X-Hub-Signature', '-1').split('=')[-1]
                print('\n~~~~~~~~~ git updating session ~~~~~~~~~\n', url, sh0)
                sh1 = hmac.new(bytes(os.environ['GIT_SECRET_KEY'], encoding='utf8'), msg=self.request.body,
                               digestmod=sha1)
                if hmac.compare_digest(sh1.hexdigest(), sh0):
                    print('OK, GITHUB CHECKED')
                    os.system('bash localdata/updater.sh')
                else:
                    print('THIS IS NOT GITHUB!')
            else:
                print('Bad args,', self.request.headers.get('X-Github-Event', '-1'), postdata.get("ref", ''))