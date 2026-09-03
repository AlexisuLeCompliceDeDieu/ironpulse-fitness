# -*- coding: utf-8 -*-
"""Génère des icônes SVG « machine seule » (aucune personne) pour machines.json.
Chaque machine reçoit une illustration simple du matériel en data-URI SVG.
"""
import base64
import json
import os

LINE_C = "#d19a63"
BG1 = "#1a1a22"
BG2 = "#26262f"

def svg(body):
    return ("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 400 400\" width=\"400\" height=\"400\">"
            "<defs><linearGradient id=\"g\" x1=\"0\" y1=\"0\" x2=\"0\" y2=\"1\">"
            "<stop offset=\"0\" stop-color=\"%s\"/><stop offset=\"1\" stop-color=\"%s\"/>"
            "</linearGradient></defs>"
            "<rect width=\"400\" height=\"400\" fill=\"url(#g)\"/>"
            "<g fill=\"none\" stroke=\"%s\" stroke-width=\"8\" stroke-linecap=\"round\" stroke-linejoin=\"round\">%s</g>"
            "</svg>" % (BG1, BG2, LINE_C, body))

def datauri(s):
    return "data:image/svg+xml;base64," + base64.b64encode(s.encode("utf-8")).decode("ascii")

def _bench():
    return ('<rect x="90" y="210" width="230" height="22" rx="10"/>'
            '<rect x="120" y="232" width="18" height="60"/>'
            '<rect x="265" y="232" width="18" height="60"/>')

def _bench_incline():
    return ('<rect x="90" y="200" width="120" height="22" rx="10"/>'
            '<rect x="205" y="175" width="120" height="22" rx="10" transform="rotate(12 205 186)"/>'
            '<rect x="130" y="222" width="18" height="70"/>'
            '<rect x="250" y="222" width="18" height="60"/>')

def _upright_frame():
    return ('<rect x="90" y="70" width="26" height="230"/>'
            '<rect x="284" y="70" width="26" height="230"/>'
            '<rect x="90" y="300" width="220" height="22"/>'
            '<line x1="103" y1="110" x2="297" y2="110"/>')

def _upright_base():
    return ('<rect x="90" y="150" width="26" height="130"/>'
            '<rect x="284" y="150" width="26" height="130"/>'
            '<rect x="90" y="280" width="220" height="24" rx="10"/>')

SHAPES = {
 # --- Pectoraux ---
 "TCG-PESC-01": _bench() +
    '<rect x="300" y="90" width="22" height="120" rx="8"/>'
    '<rect x="78" y="90" width="22" height="120" rx="8"/>'
    '<line x1="89" y1="90" x2="89" y2="60"/><line x1="311" y1="90" x2="311" y2="60"/>'
    '<rect x="70" y="45" width="34" height="20" rx="10"/><rect x="296" y="45" width="34" height="20" rx="10"/>'
    '<circle cx="140" cy="130" r="11"/><circle cx="260" cy="130" r="11"/>',
 "MTX-PECS-03": _upright_frame() +
    '<rect x="200" y="70" width="26" height="120" rx="10"/>'
    '<line x1="213" y1="120" x2="140" y2="70"/><line x1="213" y1="120" x2="260" y2="70"/>'
    '<rect x="110" y="50" width="42" height="22" rx="11"/><rect x="248" y="50" width="42" height="22" rx="11"/>',
 "TCG-PECS-02": _bench() +
    '<rect x="90" y="70" width="22" height="80"/>'
    '<path d="M112 84 C140 60 260 60 288 84"/>'
    '<rect x="288" y="70" width="22" height="80"/>',
 "MTX-PECS-06": '<title></title>' +
    '<rect x="90" y="200" width="120" height="22" rx="10"/>'
    '<rect x="205" y="230" width="120" height="22" rx="10" transform="rotate(-10 265 241)"/>'
    '<rect x="120" y="222" width="16" height="70"/><rect x="250" y="222" width="16" height="60"/>'
    '<line x1="205" y1="120" x2="260" y2="70"/><line x1="205" y1="120" x2="150" y2="70"/>'
    '<rect x="122" y="55" width="42" height="20" rx="10"/><rect x="230" y="55" width="42" height="20" rx="10"/>',
 "LIF-PECS-04": _bench_incline() +
    '<path d="M150 60 q18 70 55 78"/><path d="M250 60 q-18 70 -55 78"/>'
    '<rect x="70" y="48" width="34" height="20" rx="10"/><rect x="296" y="48" width="34" height="20" rx="10"/>',
 "PNT-PECS-07": _upright_frame() +
    '<rect x="180" y="40" width="40" height="22" rx="11"/>'
    '<line x1="200" y1="62" x2="200" y2="120"/><line x1="200" y1="120" x2="90" y2="180"/>'
    '<line x1="200" y1="120" x2="310" y2="180"/>'
    '<rect x="90" y="150" width="22" height="30"/><rect x="288" y="150" width="22" height="30"/>'
    '<line x1="200" y1="300" x2="103" y2="300"/><line x1="200" y1="300" x2="297" y2="300"/>',
 "HSM-PECS-08": _bench() +
    '<rect x="110" y="60" width="180" height="14" rx="7"/>'
    '<rect x="120" y="74" width="16" height="140"/><rect x="264" y="74" width="16" height="140"/>'
    '<circle cx="128" cy="52" r="9"/><circle cx="272" cy="52" r="9"/>',
 "BDS-PECS-09": _bench() +
    '<rect x="92" y="150" width="216" height="16" rx="8"/>'
    '<rect x="120" y="166" width="18" height="48"/><rect x="262" y="166" width="18" height="48"/>',
 "BDS-PECS-10": _bench_incline(),
 # --- Dos ---
 "MTX-DOS-01": _upright_frame() +
    '<path d="M103 70 C120 130 180 180 297 180"/>'
    '<line x1="200" y1="180" x2="200" y2="300"/>',
 "HSM-DOS-03": _upright_frame() +
    '<path d="M140 70 C140 150 260 160 297 170"/>'
    '<path d="M120 160 Q200 210 200 300"/>',
 "TCG-DOS-10": _upright_frame() +
    '<line x1="200" y1="80" x2="200" y2="300"/>'
    '<line x1="103" y1="140" x2="297" y2="110"/>'
    '<line x1="160" y1="190" x2="240" y2="230"/>',
 "TCG-DOS-02": _upright_base() +
    '<rect x="120" y="170" width="160" height="18" rx="9"/>',
 "LIF-DOS-05": '<title></title>' +
    '<rect x="110" y="150" width="28" height="120"/>'
    '<rect x="262" y="150" width="28" height="120"/>'
    '<rect x="110" y="270" width="180" height="22"/>'
    '<rect x="90" y="120" width="50" height="22" rx="11"/>'
    '<rect x="260" y="120" width="50" height="22" rx="11"/>'
    '<line x1="120" y1="135" x2="120" y2="90"/><line x1="280" y1="135" x2="280" y2="90"/>',
 "HOI-DOS-07": '<title></title>' +
    '<rect x="90" y="240" width="220" height="24" rx="10"/>'
    '<line x1="200" y1="264" x2="200" y2="90"/>'
    '<rect x="170" y="60" width="60" height="30" rx="10"/>'
    '<line x1="90" y1="252" x2="110" y2="160"/><line x1="310" y1="252" x2="290" y2="160"/>',
 "NLT-DOS-09": _upright_frame() +
    '<circle cx="200" cy="120" r="34"/>'
    '<line x1="200" y1="120" x2="140" y2="200"/><line x1="200" y1="120" x2="260" y2="200"/>'
    '<rect x="120" y="270" width="160" height="22" rx="10"/>',
 "PRE-DOS-06": _upright_base() +
    '<rect x="120" y="180" width="160" height="16" rx="8"/>'
    '<line x1="200" y1="180" x2="200" y2="120"/>',
 "LIF-DOS-08": _upright_frame() +
    '<path d="M120 70 C120 150 200 180 200 300"/>'
    '<path d="M200 70 C200 150 280 180 280 300"/>',
 # --- Épaules ---
 "TCG-EPAU-01": _upright_frame() +
    '<rect x="200" y="70" width="24" height="120" rx="10"/>'
    '<line x1="212" y1="120" x2="150" y2="70"/><line x1="212" y1="120" x2="270" y2="70"/>'
    '<rect x="118" y="52" width="46" height="20" rx="10"/><rect x="236" y="52" width="46" height="20" rx="10"/>',
 "CYB-EPAU-04": _upright_frame() +
    '<rect x="200" y="80" width="22" height="110" rx="10"/>'
    '<line x1="211" y1="120" x2="150" y2="70"/><line x1="211" y1="120" x2="250" y2="70"/>'
    '<circle cx="200" cy="60" r="26"/><circle cx="200" cy="60" r="12"/>',
 "MTX-EPAU-02": _upright_base() +
    '<line x1="103" y1="160" x2="120" y2="90"/><line x1="297" y1="160" x2="280" y2="90"/>'
    '<circle cx="120" cy="85" r="10"/><circle cx="280" cy="85" r="10"/>',
 "PNT-EPAU-03": _upright_frame() +
    '<line x1="160" y1="120" x2="160" y2="300"/><line x1="240" y1="120" x2="240" y2="300"/>'
    '<line x1="160" y1="120" x2="120" y2="80"/><line x1="240" y1="120" x2="280" y2="80"/>'
    '<rect x="90" y="60" width="40" height="18" rx="9"/><rect x="270" y="60" width="40" height="18" rx="9"/>',
 "NLT-EPAU-05": _upright_frame() +
    '<rect x="90" y="120" width="24" height="130"/><rect x="286" y="120" width="24" height="130"/>'
    '<rect x="90" y="120" width="44" height="22" rx="11"/><rect x="266" y="120" width="44" height="22" rx="11"/>'
    '<line x1="200" y1="120" x2="200" y2="70"/>',
 # --- Jambes ---
 "TCG-JAMB-01": '<title></title>' +
    '<path d="M90 300 L260 300 L90 90 Z"/>'
    '<rect x="150" y="180" width="120" height="120"/>'
    '<line x1="260" y1="300" x2="260" y2="200"/>'
    '<rect x="120" y="160" width="34" height="20" rx="10"/>',
 "PRE-JAMB-04": '<title></title>' +
    '<rect x="90" y="90" width="220" height="26" rx="12"/>'
    '<rect x="90" y="250" width="220" height="26" rx="12"/>'
    '<rect x="90" y="116" width="216" height="12"/><rect x="90" y="238" width="216" height="12"/>'
    '<rect x="60" y="150" width="34" height="34" rx="8"/><rect x="296" y="100" width="44" height="44" rx="8"/>',
 "MTX-JAMB-02": _upright_base() +
    '<rect x="170" y="120" width="60" height="40" rx="10"/>'
    '<line x1="200" y1="160" x2="200" y2="120"/>',
 "MTX-JAMB-03": _upright_base() +
    '<path d="M150 170 Q150 220 200 220 Q250 220 250 170"/>',
 "CYB-JAMB-05": '<title></title>' +
    '<rect x="110" y="130" width="180" height="20" rx="10"/>'
    '<rect x="120" y="150" width="18" height="130"/><rect x="262" y="150" width="18" height="130"/>'
    '<path d="M150 170 Q150 230 200 230 Q250 230 250 170"/>',
 "KSR-JAMB-06": '<title></title>' +
    '<rect x="120" y="120" width="160" height="20" rx="10"/>'
    '<rect x="130" y="140" width="18" height="140"/><rect x="252" y="140" width="18" height="140"/>'
    '<line x1="120" y1="180" x2="90" y2="180"/><line x1="280" y1="180" x2="310" y2="180"/>'
    '<rect x="70" y="165" width="26" height="30" rx="8"/><rect x="304" y="165" width="26" height="30" rx="8"/>',
 "TCG-JAMB-07": '<title></title>' +
    '<rect x="120" y="120" width="160" height="20" rx="10"/>'
    '<rect x="130" y="140" width="18" height="140"/><rect x="252" y="140" width="18" height="140"/>'
    '<line x1="120" y1="200" x2="90" y2="120"/><line x1="280" y1="200" x2="310" y2="120"/>'
    '<rect x="70" y="100" width="26" height="34" rx="8"/><rect x="304" y="100" width="26" height="34" rx="8"/>',
 "LIF-JAMB-08": '<title></title>' +
    '<path d="M90 300 L250 300 L250 220 L180 220 L180 120 L300 120 L300 220 L250 220"/>'
    '<rect x="140" y="150" width="160" height="40" rx="8"/>'
    '<line x1="90" y1="300" x2="310" y2="300"/>',
 "MTX-JAMB-09": _upright_frame() +
    '<rect x="120" y="170" width="160" height="90" rx="8"/>'
    '<line x1="200" y1="170" x2="200" y2="120"/>',
 "BDS-JAMB-10": '<title></title>' +
    '<rect x="90" y="130" width="220" height="22" rx="10"/>'
    '<rect x="200" y="152" width="22" height="90"/>'
    '<rect x="90" y="150" width="34" height="60" rx="8"/><rect x="276" y="150" width="34" height="60" rx="8"/>'
    '<rect x="206" y="300" width="10" height="40"/><rect x="90" y="300" width="200" height="14"/>',
 "HOI-JAMB-11": '<title></title>' +
    '<rect x="90" y="300" width="220" height="16"/>'
    '<rect x="200" y="140" width="20" height="160"/>'
    '<rect x="90" y="130" width="220" height="20" rx="10"/>'
    '<rect x="120" y="150" width="30" height="80" rx="8"/><rect x="250" y="150" width="30" height="80" rx="8"/>',
 "TCG-JAMB-15": _upright_frame() +
    '<path d="M140 120 L200 120 L200 220 L300 220 L300 120 L140 120 Z"/>'
    '<line x1="200" y1="120" x2="200" y2="60"/>',
 "RGE-JAMB-13": '<title></title>' +
    '<rect x="110" y="190" width="180" height="24" rx="10"/>'
    '<path d="M110 214 L110 150 L170 150 L170 190"/>'
    '<rect x="120" y="214" width="24" height="46"/><rect x="256" y="214" width="24" height="46"/>',
 "NLT-JAMB-14": '<title></title>' +
    '<rect x="110" y="200" width="180" height="22" rx="10"/>'
    '<rect x="120" y="222" width="20" height="60"/><rect x="260" y="222" width="20" height="60"/>'
    '<line x1="200" y1="200" x2="200" y2="150"/>'
    '<circle cx="200" cy="140" r="12"/>',
 "PNT-JAMB-12": _bench() +
    '<rect x="170" y="120" width="60" height="24" rx="10"/>'
    '<rect x="200" y="144" width="24" height="66"/>',
 "HOI-JAMB-16": '<title></title>' +
    '<rect x="90" y="120" width="220" height="24" rx="10"/>'
    '<line x1="90" y1="132" x2="90" y2="300"/><line x1="310" y1="132" x2="310" y2="300"/>'
    '<line x1="90" y1="300" x2="310" y2="300"/>'
    '<circle cx="120" cy="200" r="12"/><circle cx="280" cy="200" r="12"/>',
 "RGE-JAMB-16": '<title></title>' +
    '<rect x="90" y="80" width="26" height="220"/>'
    '<rect x="284" y="80" width="26" height="220"/>'
    '<rect x="90" y="300" width="220" height="20"/>'
    '<line x1="103" y1="120" x2="297" y2="120"/>'
    '<line x1="103" y1="160" x2="297" y2="160"/><line x1="103" y1="200" x2="297" y2="200"/>',
 "RGE-JAMB-17": '<title></title>' +
    '<rect x="90" y="90" width="26" height="210"/>'
    '<rect x="284" y="90" width="26" height="210"/>'
    '<rect x="90" y="300" width="220" height="20"/>'
    '<line x1="103" y1="130" x2="297" y2="130"/>'
    '<rect x="120" y="190" width="160" height="18" rx="9"/>',
 # --- Bras ---
 "TCG-BRAS-01": '<title></title>' +
    '<rect x="140" y="90" width="120" height="16" rx="8"/>'
    '<rect x="200" y="106" width="22" height="140"/>'
    '<rect x="195" y="246" width="32" height="40" rx="8"/>'
    '<rect x="140" y="90" width="16" height="120"/><rect x="244" y="90" width="16" height="120"/>',
 "HOI-BRAS-03": '<title></title>' +
    '<rect x="120" y="200" width="160" height="20" rx="10"/>'
    '<rect x="200" y="150" width="20" height="50"/>'
    '<rect x="150" y="120" width="100" height="26" rx="12"/>'
    '<line x1="200" y1="146" x2="200" y2="90"/>'
    '<rect x="60" y="300" width="280" height="16"/>',
 "PRE-BRAS-04": '<title></title>' +
    '<rect x="90" y="240" width="90" height="22" rx="10"/>'
    '<rect x="180" y="120" width="30" height="142" rx="6"/>'
    '<rect x="205" y="130" width="110" height="20" rx="9"/>'
    '<line x1="150" y1="240" x2="150" y2="300"/><line x1="90" y1="300" x2="310" y2="300"/>',
 "TCG-BRAS-02": '<title></title>' +
    '<rect x="90" y="90" width="220" height="20" rx="10"/>'
    '<line x1="200" y1="110" x2="200" y2="150"/>'
    '<rect x="180" y="150" width="40" height="40" rx="6"/>'
    '<rect x="190" y="190" width="20" height="60"/>',
 "MTX-BRAS-05": _upright_frame() +
    '<path d="M140 160 C140 220 160 240 200 240 C240 240 260 220 260 160"/>'
    '<line x1="200" y1="180" x2="200" y2="240"/>',
 "HSM-BRAS-06": '<title></title>' +
    '<rect x="90" y="120" width="220" height="22" rx="10"/>'
    '<line x1="90" y1="131" x2="90" y2="300"/><line x1="310" y1="131" x2="310" y2="300"/>'
    '<rect x="90" y="300" width="220" height="18"/>'
    '<line x1="140" y1="150" x2="140" y2="200"/><line x1="260" y1="150" x2="260" y2="200"/>',
 "ELE-BRAS-07": '<title></title>' +
    '<rect x="70" y="200" width="260" height="16" rx="8"/>'
    '<rect x="88" y="160" width="18" height="44" rx="6"/><rect x="294" y="160" width="18" height="44" rx="6"/>'
    '<circle cx="78" cy="208" r="14"/><circle cx="322" cy="208" r="14"/>'
    '<rect x="70" y="130" width="20" height="30" rx="5"/><rect x="310" y="130" width="20" height="30" rx="5"/>',
 "ELE-BRAS-08": _upright_frame() +
    '<rect x="90" y="120" width="220" height="20" rx="10"/>'
    '<rect x="90" y="140" width="20" height="140"/><rect x="290" y="140" width="20" height="140"/>'
    '<path d="M130 130 L130 200 L170 200 L170 130"/>'
    '<path d="M230 130 L230 200 L270 200 L270 130"/>',
 # --- Core ---
 "TCG-CORE-01": _upright_base() +
    '<rect x="150" y="150" width="100" height="22" rx="10"/>'
    '<path d="M150 172 Q150 210 200 210 Q250 210 250 172"/>',
 "HOI-CORE-03": _upright_base() +
    '<rect x="150" y="150" width="100" height="22" rx="10"/>',
 "MTX-CORE-02": _upright_base() +
    '<line x1="200" y1="150" x2="200" y2="80"/>'
    '<rect x="150" y="60" width="100" height="22" rx="10"/>',
 "RGE-CORE-03": '<title></title>' +
    '<rect x="90" y="190" width="80" height="22" rx="10"/>'
    '<path d="M170 200 C210 230 210 280 200 300"/>'
    '<rect x="200" y="300" width="20" height="20"/>'
    '<rect x="120" y="300" width="180" height="16"/>',
 "PNT-CORE-04": '<title></title>' +
    '<rect x="160" y="120" width="80" height="20" rx="10"/>'
    '<line x1="200" y1="140" x2="200" y2="300"/>'
    '<rect x="180" y="300" width="40" height="18" rx="8"/>'
    '<rect x="200" y="70" width="12" height="50"/>'
    '<line x1="200" y1="70" x2="170" y2="45"/><line x1="200" y1="70" x2="230" y2="45"/>',
 "XFT-CORE-05": '<title></title>' +
    '<rect x="90" y="110" width="220" height="24" rx="10"/>'
    '<line x1="90" y1="122" x2="90" y2="300"/><line x1="310" y1="122" x2="310" y2="300"/>'
    '<rect x="90" y="300" width="220" height="18"/>'
    '<circle cx="140" cy="200" r="13"/><circle cx="260" cy="200" r="13"/>',
 "RGE-CORE-05": '<title></title>' +
    '<rect x="90" y="230" width="220" height="20" rx="10"/>'
    '<path d="M130 230 C130 170 270 170 270 230 Z"/>'
    '<line x1="130" y1="180" x2="200" y2="160"/>'
    '<rect x="190" y="140" width="20" height="26" rx="8"/>',
 # --- Cardio ---
 "TCG-CARD-01": '<title></title>' +
    '<rect x="90" y="210" width="220" height="18" rx="8"/>'
    '<rect x="90" y="230" width="60" height="70" rx="10"/>'
    '<rect x="250" y="230" width="60" height="70" rx="10"/>'
    '<line x1="200" y1="210" x2="200" y2="300"/>'
    '<rect x="90" y="140" width="100" height="24" rx="8"/>'
    '<line x1="190" y1="152" x2="310" y2="152"/>',
 "LIF-CARD-07": 'TCG_CARD_01_PLACEHOLDER',
 "TCG-CARD-02": '<title></title>' +
    '<circle cx="200" cy="180" r="70"/>'
    '<circle cx="200" cy="180" r="30"/>'
    '<rect x="200" y="110" width="22" height="190"/>'
    '<rect x="200" y="300" width="80" height="18" rx="8"/>'
    '<rect x="120" y="130" width="16" height="40" rx="6"/><rect x="264" y="130" width="16" height="40" rx="6"/>',
 "LIF-CARD-12": '<title></title>' +
    '<circle cx="150" cy="240" r="55"/>'
    '<circle cx="150" cy="240" r="24"/>'
    '<rect x="90" y="300" width="90" height="16"/>'
    '<rect x="210" y="215" width="110" height="16" rx="8"/>'
    '<line x1="210" y1="200" x2="300" y2="200"/><line x1="210" y1="245" x2="300" y2="245"/>'
    '<rect x="120" y="90" width="18" height="40" rx="6"/><rect x="264" y="90" width="18" height="40" rx="6"/>',
 "MTX-CARD-03": '<title></title>' +
    '<rect x="90" y="280" width="220" height="20" rx="8"/>'
    '<rect x="120" y="250" width="40" height="30" rx="6"/>'
    '<line x1="160" y1="260" x2="290" y2="200"/>'
    '<rect x="285" y="185" width="26" height="26" rx="6"/>'
    '<line x1="90" y1="290" x2="90" y2="250"/><line x1="310" y1="290" x2="310" y2="250"/>',
 "C2C-CARD-04": 'MTX_CARD_03_COPY',
 "TCG-CARD-13": '<title></title>' +
    '<rect x="90" y="280" width="220" height="20" rx="8"/>'
    '<rect x="120" y="250" width="40" height="30" rx="6"/>'
    '<line x1="160" y1="260" x2="290" y2="200"/>'
    '<rect x="285" y="185" width="26" height="26" rx="6"/>'
    '<circle cx="160" cy="230" r="26"/><line x1="160" y1="256" x2="160" y2="280"/>',
 "STM-CARD-05": '<title></title>' +
    '<rect x="140" y="120" width="120" height="180" rx="10"/>'
    '<line x1="140" y1="150" x2="260" y2="150"/><line x1="140" y1="190" x2="260" y2="190"/>'
    '<line x1="140" y1="230" x2="260" y2="230"/><line x1="140" y1="270" x2="260" y2="270"/>'
    '<rect x="155" y="60" width="16" height="60" rx="6"/><rect x="229" y="60" width="16" height="60" rx="6"/>',
 "RGE-CARD-06": '<title></title>' +
    '<circle cx="200" cy="200" r="52"/>'
    '<rect x="200" y="120" width="20" height="130"/>'
    '<rect x="90" y="120" width="24" height="80" rx="8"/>'
    '<rect x="286" y="120" width="24" height="80" rx="8"/>'
    '<rect x="200" y="250" width="80" height="60" rx="8"/>'
    '<line x1="90" y1="120" x2="120" y2="60"/><line x1="310" y1="120" x2="280" y2="60"/>',
 "MTX-CARD-08": '<title></title>' +
    '<rect x="90" y="230" width="220" height="16" rx="8"/>'
    '<rect x="90" y="246" width="60" height="54" rx="8"/>'
    '<rect x="250" y="246" width="60" height="54" rx="8"/>'
    '<circle cx="110" cy="170" r="26"/><circle cx="290" cy="170" r="26"/>'
    '<line x1="110" y1="250" x2="290" y2="250"/>'
    '<rect x="200" y="150" width="10" height="100"/>'
    '<rect x="150" y="60" width="60" height="20" rx="8"/>',
 "PRE-CARD-09": 'MTX_CARD_08_COPY',
 "C2C-CARD-10": '<title></title>' +
    '<rect x="90" y="90" width="220" height="20" rx="10"/>'
    '<line x1="200" y1="110" x2="200" y2="150"/>'
    '<rect x="180" y="150" width="40" height="60" rx="6"/>'
    '<line x1="200" y1="210" x2="200" y2="300"/>'
    '<rect x="150" y="300" width="100" height="18" rx="8"/>',
 "CYB-CARD-11": '<title></title>' +
    '<circle cx="200" cy="180" r="66"/>'
    '<circle cx="200" cy="180" r="28"/>'
    '<rect x="200" y="114" width="22" height="186"/>'
    '<rect x="150" y="60" width="100" height="24" rx="8"/>'
    '<line x1="200" y1="60" x2="200" y2="114"/>',
 "BDS-CARD-14": '<title></title>' +
    '<rect x="120" y="120" width="160" height="180"/>'
    '<line x1="120" y1="160" x2="280" y2="160"/><line x1="120" y1="200" x2="280" y2="200"/>'
    '<line x1="120" y1="240" x2="280" y2="240"/><line x1="120" y1="280" x2="280" y2="280"/>'
    '<line x1="120" y1="120" x2="120" y2="300"/><line x1="280" y1="120" x2="280" y2="300"/>'
    '<circle cx="120" cy="120" r="14"/><circle cx="280" cy="300" r="14"/>',
}

# remplace les placeholders de copie
SHAPES["LIF-CARD-07"] = SHAPES["TCG-CARD-01"]
SHAPES["C2C-CARD-04"] = SHAPES["MTX-CARD-03"]
SHAPES["PRE-CARD-09"] = SHAPES["MTX-CARD-08"]

DEFAULT_SHAPE = "TCG-CARD-02"

def main():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "machines.json")
    with open(path, "r", encoding="utf-8") as f:
        machines = json.load(f)
    for m in machines:
        shape = SHAPES.get(m["code"]) or SHAPES.get(DEFAULT_SHAPE)
        m["image_url"] = datauri(svg(shape))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(machines, f, ensure_ascii=False, indent=2)
    print("machines écrites:", len(machines))

if __name__ == "__main__":
    main()