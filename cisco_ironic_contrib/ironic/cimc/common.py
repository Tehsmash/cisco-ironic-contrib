# Copyright 2015, Cisco Systems.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_log import log as logging
from oslo_utils import importutils

from ironic.drivers.modules.cimc import common

imcsdk = importutils.try_import('ImcSdk')

LOG = logging.getLogger(__name__)

NUMBER_OF_UPLINKS = 2


def add_vnic(task, vnic_id, mac, vlan, pxe=False, uplink=None):
    name = "eth%d" % vnic_id
    uplink = uplink if uplink else vnic_id % NUMBER_OF_UPLINKS
    with common.cimc_handle(task) as handle:
        rackunit = handle.get_imc_managedobject(
            None, imcsdk.ComputeRackUnit.class_id())
        adaptorunits = handle.get_imc_managedobject(
            in_mo=rackunit, class_id=imcsdk.AdaptorUnit.class_id())

        dn = "%s/host-eth-%s" % (adaptorunits[0].Dn, name)

        method = imcsdk.ImcCore.ExternalMethod("ConfigConfMo")
        method.Cookie = handle.cookie
        method.Dn = dn

        config = imcsdk.Imc.ConfigConfig()

        newVic = imcsdk.ImcCore.ManagedObject("adaptorHostEthIf")
        newVic.set_attr("name", name)
        newVic.set_attr("mtu", "1500")
        newVic.set_attr("pxeBoot", "enabled" if pxe else "disabled")
        newVic.set_attr("Dn", dn)
        newVic.set_attr("mac", mac if mac else "AUTO")
        newVic.set_attr("uplinkPort", str(uplink))

        vlanProfile = imcsdk.ImcCore.ManagedObject("adaptorEthGenProfile")
        vlanProfile.set_attr("vlanMode", "ACCESS")
        vlanProfile.set_attr("vlan", str(vlan) if vlan else "NONE")
        vlanProfile.set_attr("Dn", dn)

        newVic.add_child(vlanProfile)
        config.add_child(newVic)
        method.InConfig = config

        resp = handle.xml_query(
            method, imcsdk.WriteXmlOption.DIRTY)
        error = getattr(resp, 'error_code', None)
        if error:
            raise imcsdk.ImcException(node=task.node.uuid, error=error)


def delete_vnic(task, vnic_id):
    if vnic_id < NUMBER_OF_UPLINKS:
        clean_vnic(task, vnic_id)
    else:
        name = "eth%d" % vnic_id
        with common.cimc_handle(task) as handle:
            rackunit = handle.get_imc_managedobject(
                None, imcsdk.ComputeRackUnit.class_id())
            adaptorunits = handle.get_imc_managedobject(
                in_mo=rackunit, class_id=imcsdk.AdaptorUnit.class_id())
            vic = {
                "Dn": "%s/host-eth-%s" % (adaptorunits[0].Dn, name),
            }
            handle.remove_imc_managedobject(
                None, class_id="adaptorHostEthIf", params=vic)


def clean_vnic(task, vnic_id):
    add_vnic(task, vnic_id, None, None)
