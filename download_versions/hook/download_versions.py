#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2021 Walt Jones walt@nspacedesign.com
# Written for Clean Plate FX 15 November 2021

import datetime
import logging

from ftrack_action_handler.action import BaseAction
import ftrack_api
import urllib
from pathlib import Path
import os

def send_message_to_user(session, user_id, messageTxt):
    # Send a message to the active user
    session.event_hub.publish(
        ftrack_api.event.base.Event(
            topic='ftrack.action.trigger-user-interface',
            data=dict(
                type='message',
                success=True,
                message=(messageTxt)
            ),
            target='applicationId=ftrack.client.web and user.id="{0}"'.format(user_id)
        ),
        on_error='ignore'
    )

class DownloadVersions(BaseAction):

    label = 'Download Versions'
    identifier = 'waltjones.download.versions'
    description = 'Download selected versions'

    def discover(self, session, entities, event):
        # Only show this for Versions when a selection has been made
        if not entities:
            return False

        for entity_type, entity_id in entities:
            if entity_type == 'AssetVersion':
                return True        

        return True

    def launch(self, session, entities, event):
        server_location = session.query('Location where name is "ftrack.server"').one()
        review_location = session.query('Location where name is "ftrack.review"').one()
        locations = [server_location, review_location]
        downloadRootPath = str(Path.home() / "Downloads")
        fileTypes = [".mov", ".mp4"]
        userID = event['source'].get('user', {}).get('id', None) #Current User ID
        downloads = list()

        send_message_to_user(session, userID, "Building list of media to download...")
        send_message_to_user(session, userID, "Please be patient - this can take awhile")

        # Get a list of currently selected versions
        versionIDs = []
        for entity in entities:
            versionIDs.append(entity[1])

        # Get details for these versions to build a list of media to download
        for version in session.query('AssetVersion where id in {0}'.format("(" + ','.join(["'{}'".format(value) for value in versionIDs]) + ")")):
            for component in version.get("components"):
                
                # If this component is of the right fileType, then download it
                fileType = component.get("file_type")
                print(fileType)
                if fileType in fileTypes:
                    
                    # Check if we have a version name that seems to match the component name
                    versionName = version.get("_link")[-1]["name"].replace(" ", "_")
                    if versionName[0:10] == component.get("name")[0:10]:
                        # Don't put the version name in the filename
                        fileName = component.get("name") + fileType
                    else:
                        # Put the version name in the filename
                        fileName = versionName.replace(" ", "_") + "_" + component.get("name") + fileType

                    # Calculate the full download path and URL to pull from
                    downloadPath = os.path.join(downloadRootPath, fileName)
                    for location in locations:
                        try:
                            url = location.get_url(component)
                            # url = component.get("component_locations")[0].get("url")["value"]
                        except:
                            url = None
                        if url:
                            # Push this pair onto the download list
                            downloads.append((fileName, url, downloadPath))

        # Now that we have a full list of stuff to download, do it!
        downloadNum = 0
        for fileDownload in downloads:
            downloadNum += 1
            # Download the file
            send_message_to_user(session, userID, "Downloading " + str(downloadNum) + " of " + str(len(downloads)) + ": " + fileDownload[0] + "...")
            urllib.request.urlretrieve(fileDownload[1], fileDownload[2])

        return {
            'success': True,
            'message': 'Download Complete: ' + str(len(downloads)) + ' media files from ' + str(len(versionIDs)) + ' versions',
            'type': 'message'
        }


def register(session, **kw):
    '''Register plugin.'''
    if not isinstance(session, ftrack_api.Session):
        return

    action = DownloadVersions(session)
    action.register()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)

    session.event_hub.wait()
