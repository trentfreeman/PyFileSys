import BlockDevice
import os
import numpy 
from struct import *
import math

class FileSystem:

    @staticmethod
    def createFileSystem(filename, numBlocks, sizeBlocks = 1024):
        #This will always create a new file system. 
        #CREATE MASTER BLOCK with settings as given below
        if sizeBlocks < numBlocks//8 or sizeBlocks < 27:
            print("Your blocks size is too small to fit either the block map or the master block. Please make the Block size bigger")
            return
        bd = BlockDevice.BlockDevice(filename, numBlocks, sizeBlocks, True)
        flags = [False] * 8 
        flagArray = numpy.packbits(flags)
        magicNum = 44973
        numInodes = 1
        blkBlockMap = 1
        blkInodeMap = 2
        #Im going to have the data blocks grow backwards. and I nodes grow forwards
        blkRoot = numBlocks
        bd.write_block(0, buff, True)
        buff = bytearray(pack('IHHIIIII', magicNum, sizeBlocks, numInodes, numBlocks, blkBlockMap, blkInodeMap, blkRoot, flagArray[0]))
        #CREATE BLOCK MAP. Initially it is empty except for the first 3 blocks, which have the master, block map, and inode map respectively 
        #I am just a initiallizing the first 4 bits to 1111 adding the rest of the number of blocks to it using the same method from the flag array 
        blockMap = [True] * 3 + [False] * (numBlocks-3)
        blockMapArr = bytearray(pack('?', blockMap[0]))
        blockMap = blockMap[1:]
        for item in blockMap:
            blockMapArr += bytearray(pack('?', item))
        bd.write_block(1, blockMapArr, True)
        #CREATE INODEMAP. The first inode will be the only one to exist initially, so that is the only one to write initially.
        InodeNum = 0
        Cdate = 0
        Mdate = 0
        #flags for each setting: 0xF4 = FR(EE) 244, 0xF1 = FI(LE) 241, 0xD1 = DI(R)209, 0x5b = s(ym)b(olic) link 92, 0xB1 = BL(OCK)177,  0xDA = DA(TA) 218   
        Flag = 244
        Perms = 0
        Level = 0
        padding = 0
        #this has this structure because it the alignment of bytes
        iNodeBytes = bytearray(pack('IIHHBBH', Cdate, Mdate, InodeNum, Perms, Flag, Level, padding))
        #there are 28 possible block pointers, initialize them all to zero (done with a for lop to make more readable)
        iNodeBytes += bytearray(pack('I',0))
        for item in range(1,28):
            iNodeBytes += bytearray(pack('I',0))
        bd.write_block(2, iNodeBytes, True)
        bd.close()


#Thoughts of what to do: rewrite master block and write out 
# rewrite each block individually and write out (block map from blockMap object and Inode array from Inode methods
#TODO: IMPLEMENT WRITE OF DIRTY BIT
#Thoughts on dirty bit: figure out how to add the bit bad to readin (may just have to manually sove in) then write back


############## BASE FILE SYSTEM METHODS##########################################################################

#init will be called when the command prompt calls mount
    def __init__(self, filename):
        #search for the file
        if not(filename in os.listdir('.')):
            print("Could not find device, please try again")
        self.bd = BlockDevice.BlockDevice(filename)
        readin = bytearray(self.bd.blocksize)
        self.bd.read_block(0, readin)
        print(self.bd.blocksize)
        #read in all variables from the master block and make them easy to use ints
        (self.magicNum, self.blockSize, self.numInodes, self.numBlocks, self.blockMapNum, self.blockInodeMap, self.blockRoot) = unpack('IHHIIII', readin[0:24])
        #set up flag array
        self.flagArray = bytearray(readin[24:25])
        #set dirty bit when mounted
        self.flagArray[0] = 1 
        #initialize the blockMap object
        blockMapArr = bytearray(self.blockSize)
        self.bd.read_block(self.blockMapNum, blockMapArr)
        self.blockMap = blockMap(blockMapArr, self.numBlocks)
        #initialize the INode array
        iNodeBytes = bytearray()
        buff = bytearray(self.blockSize)
         #if there are more I nodes than fit in a single block, they are in a different block. add that to the byte array.
        for i in range(0, math.ceil(self.numInodes/(self.blockSize/128))):
            self.bd.read_block(self.blockInodeMap+i, buff)
            iNodeBytes += buff
        self.InodeArray = INode.getInodeList(iNodeBytes, self.numInodes)


#TODO: IMPLEMENT MOUNT
    def unmount(self):
        #TODO: NEED TO CHANGE DIRTY BLOCK BACK TO FALSE
        #pack the masterblock into bytearray and change the dirty bit back to 0 for false
        self.flagArray[0] = 0
        flags = numpy.packbits(self.flagArray)
        masterBuff = bytearray(pack('IHHIIIII', self.magicNum, self.blockSize, self.numInodes, self.numBlocks, self.blockMapNum, self.blockInodeMap, self.blockRoot, flags))
        self.bd.write_block(0, masterBuff,True)
        #Master block written, write out block map
        BMbuff = bytearray(self.blockSize)
        BMbuff = self.blockMap.getBLockMapBytes(self.blockSize)
        self.bd.write_block(0, BMbuff, True)
        #Writing the iNodes back out.
        numInodesInBlock= self.blockSize/128
        iNodeBuff = bytearray(self.blockSize)
        count = 0 
        for iNode in self.INodeArray:
            iNodeBuff[(count%numInodesInBlock)*128:((count%numInodesInBlock)+1)*128] = iNode.iNodeAsBytes()
            count+=1
            if count % numInodesInBLock == 0:
                self.bd.write_block(self.blockInodeMap + count//numInodesInBlock, iNodeBuff, True)
        #it finished all the I nodes but didnt write the last block because it is not full of Inodes
        if count% numInodesInBlock != 0:
            badd = bytearray(128 * (numInodesInBlock - count%numInodesInBlock))
            iNodeBuff[((count%numInodesInBlock) +1)*128:] = badd
            self.bd.write_block(self.blockInodeMap +count//numInodesInBlock, iNodeBuff, True]


            




########## INODE METHOD CALLS  ##################################################################################
    def getInodeMap(self):
        print('| INode # | Flag  |')
        for iNode in self.InodeArray:
            print(iNode.getStatusAsString())
    
    def alloc_INode(self, typeLetter):
        #the current Inode number is one less than the number of Inodes because of array syntax
        InodeNum = self.numInodes
        self.numInodes+=1
        Cdate = 0
        Mdate = 0
        #flags for each setting: 0xF4 = FR(EE) 244, 0xF1 = FI(LE) 241, 0xD1 = DI(R)209, 0x5b = s(ym)b(olic) link 92, 0xB1 = BL(OCK)177,  0xDA = DA(TA) 218  
        if typeLetter == '0':
            Flag = 244
        elif typeLetter == 'f':
            Flag = 241
        elif typeLetter == 'd':
            Flag = 209
        elif typeLetter == 's':
            Flag = 92
        elif typeLetter == 'b':
            Flag = 177
        elif typeLetter == 'D':
            Flag = 218
        else:
            print('This letter is undefined, please try again')
            return
        Perms = 0
        Level = 0
        padding = 0
        #this has this structure because it the alignment of bytes
        iNodeBytes = bytearray(pack('IIHHBBH', Cdate, Mdate, InodeNum, Perms, Flag, Level, padding))
        #there are 28 possible block pointers, initialize them all to zero (done with a for lop to make more readable)
        iNodeBytes += bytearray(pack('I',0))
        for item in range(1,28):
            iNodeBytes += bytearray(pack('I',0))
        x = INode(iNodeBytes)
        self.InodeArray += [x]

    def free_INode(self, num):
        if num == 0:
            resp = input("ARE YOU SURE YOU WANT TO FREE THE ROOT INODE? (y/n)")
            if resp == 'n':
                print('Good Choice.')
                return
            elif resp != 'y':
                print('I didnt quite get that. Please try again')
                return
        if num < self.numInodes and num >=0:
            self.InodeArray[num].free()
        else:
            print("This is not a valid inode number. Please try again")




########## BLOCKMAP METHOD CALLS ################################################################################
    def getBlockMap(self):
        self.blockMap.printBlockMap()

    def alloc_Block(self):
        self.blockMap.alloc_block()

    def free_Block(self, num):
        self.blockMap.free_block(num)

########## BLOCK MAP CLASS   ####################################################################################
class blockMap:

    def __init__(self, blockMapArr, numBlocks):
        self.blockMapArr = blockMapArr
        self.numBlocks = numBlocks

    def printBlockMap(self):
        #simple code to print the block map with | every 8 bits and new line every 64
        count = 0 
        for item in self.blockMapArr:
            print(item, end = "")
            count+=1
            if count % 8 == 0 and not(count%64 == 0):
                print('|', end ="")
            if count%64 == 0:
                print("")
            if count > self.numBlocks:
                break

    def alloc_block(self):
        count = 0 
        while self.blockMapArr[count] != 0:
            count+=1
        self.blockMapArr[count] = 1
        return count


    def free_block(self, num):
    #dont need to empty data out of block
        if num < 4:
            resp = input('WARNING: THIS IS AN IMPORTANT BLOCK CONTAINING STRUCTURE OF THE FILE SYSTEM. ARE YOU SURE YOU WANT TO DELETE THIS BLOCK? (y/n)')
            if resp == 'n':
                return
            elif resp != 'y':
                print("I didn't quite get that. Could you please repeat the command?")
                return
        self.blockMapArr[num] = 0
        print('Block Freed')

    def makeBlockMapByte(self):
        


########### INODE CLASS   #########################################################################################
class INode:

    @staticmethod
    def getInodeList(INodeBytes, numINodes):
        retArr = [INode(INodeBytes[i*128:(i+1)*128]) for i in range(0,numINodes)]
        return retArr

    def __init__(self, iNodeBlock):
        (self.Cdate, self.Mdate, self.InodeNum, self.Perms, self.Flag, self.Level, self.padding) = unpack("IIHHBBH", iNodeBlock[0:16])
        self.data = iNodeBlock[16:]

    def getStatusAsString(self):
        #flags for each setting: 0xF4 = FR(EE) 244, 0xF1 = FI(LE) 241, 0xD1 = DI(R)209, 0x5b = s(ym)b(olic) link 92, 0xB1 = BL(OCK)177,  0xDA = DA(TA) 218 
        retString = "|   " +str(self.InodeNum)+"     |"
        if self.Flag == 244:
            retString+= '   0   |'
        elif self.Flag == 241:
            retString+= '   f   |'
        elif self.Flag == 209:
            retString+= '   d   |'
        elif self.Flag == 92:
            retString+= '   s   |'
        elif self.Flag == 218:
            retString+= '   D   |'
        elif self.Flag ==177:
            retString+= '   b   |'
        return retString

    def iNodeAsBytes(self):
        retBytes = bytearray(128)
        retBytes = pack('IIHHBBH', self.Cdate, self.Mdate, sef.InodeNum, self.Perms, self.Flag, self.Level, self.padding)
        retBytes[16:] = self.data
        return retBytes

    def free(self):
        self.Flag = 244
