*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*-*-* Basic model for PVISOR testing                                      *-*-* 
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*
* Basic model
*
* The model is a pipe with two time dependent volumes. The flow in the pipe 
* is ramped up with a time dependent junction in 10 seconds.
*
* The basic model contains the following sections:
*
* 1. Model options
* 2. Components:
*   001, tmdpvol, inlet     : The inlet boundary conditions
*   002, tmpjun , in2pipe   : Time dependent junction from inlet to pipe
*   003, sngljun, pipe      : Pipe
*   004, sngljun, pipe2out  : Junction from pipe to the outlet
*   005, tmdpvol, outlet    : The outlet boundary conditions
* 3. Time step data

*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
* Model options                                                               *
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
* Simulation type
100           new       transnt
*

*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*-*-* Components                                                          *-*-* 
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*  Title:   Inlet time dependent volume
* Number:   001
*   Type:   tmpdvol
*              
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*                name          type
0010000         inlet       tmdpvol
*                area        length           vol
0010101     1.7437e-4           1.0           0.0
*            az-angle     inc-angle     elevation
0010102           0.0          90.0           1.0
*               rough            hd       tlpvbfe
0010103        1.0e-5       14.9e-3             0
*                nebt
0010200          0003
*                Time         press          temp
0010201           0.0         1.981e7       628.2
*

*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*  Title:   Inlet time dependent junction
* Number:   002
*   Type:   tmdpjun
*              
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*              name         type
0020000      in2inp      tmdpjun
*                from         to      area        jefvcahs
0020101        001010002  003010001   1.7437e-4           0
*                 massflow
0020200             1
*            time        G_l      G_v     v_int
0020201       0.0        0.0      0.0       0.0
0020202      10.0    5.41e-1      0.0       0.0
*

*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*  Title:   Pipe
* Number:   005
*   Type:   pipe
*              
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*                name         type
0030000          pipe         pipe
*                nvol
0030001            10
*                Area     v#
0030101     1.7437e-4     10
*              length     v#
0030301         0.025     10
*           angle       v#
0030601     90.0        10
*       roughnes  hydrdiam  v#
0030801     1e-5   14.9e-3  10
*        tlpvbfe  v#
0031001        0  10
*        ef0cahs j#
0031101     1000  9
*         EBT         P         T   W4   W5   W6  v#
0031201   003   1.981e7     628.2  0.0  0.0  0.0  10
*           massflow
0031300     1
*            G_l  G_v  v_inter  j#
0031301  5.41e-1  0.0      0.0   9

*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*  Title:   Junction from pipe to outlet
* Number:   004
*   Type:   SNGLJUN
*              
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*              name         type
0040000    pipe2out      sngljun

*              FROM        TO  JUN.AREA  K.FORW K.REV JEFVCAHS
0040101   003100002 005010001       0.0     0.0   0.0        0
*         flow      G_l  G_v  v_inter
0040201      1  5.41e-1  0.0      0.0

*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*  Title:   Outlet time dependent volume
* Number:   005
*   Type:   tmpdvol
*              
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*              name         type
0050000       outlet      tmdpvol
* 101-103: See inlet tmdpvol for choises made
*                area        length           vol
0050101     1.7437e-4           1.0           0.0
*            az-angle     inc-angle     elevation
0050102           0.0          90.0           1.0
*               rough            hd       tlpvbfe
0050103        1.0e-5       14.9e-3             0
*
*                nebt
0050200          0003
*
* 201    : pressure slightly lower than inlet to allow flow to flow
*                Time         press          temp
0050201           0.0         1.781e7       628.2

*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*-*-* Timestep data                                                       *-*-* 
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*         t-end      dt-min    dt-max    control     plt    edit    rest
0000201    20.0      1.0e-9      0.01      00019      10    1000    1000
.